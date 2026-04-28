"""
The Video Processor Worker.

This script:
1. Connects to Kafka and listens for messages on "video-processing-jobs"
2. When a message arrives, downloads the video from MinIO
3. Uses FFmpeg to transcode it into 3 quality levels (360p, 720p, 1080p)
4. Each level is split into 6-second HLS segments
5. Uploads all segments to MinIO
6. Creates a master HLS playlist
7. Updates the database to mark the video as "ready"

This runs as a long-lived process (it never exits on its own).
"""
import os
import json
import shutil
import subprocess
import time
from pathlib import Path
from confluent_kafka import Consumer, KafkaException, KafkaError

from storage import download_file, upload_file_from_disk, RAW_BUCKET, PROCESSED_BUCKET
from database import update_video_status

KAFKA_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:29092")
TOPIC = "video-processing-jobs"
TMP_DIR = Path("/tmp/processing")

# ─── Quality Level Definitions ────────────────────────────────────────────────
# These define the different video qualities we create.
# Bandwidth is in bits/second — used in the HLS master playlist.
QUALITY_LEVELS = [
    {
        "name": "360p",
        "resolution": "640:360",      # width:height
        "video_bitrate": "800k",
        "audio_bitrate": "96k",
        "bandwidth": 800000,          # for master playlist
    },
    {
        "name": "720p",
        "resolution": "1280:720",
        "video_bitrate": "2500k",
        "audio_bitrate": "128k",
        "bandwidth": 2500000,
    },
    {
        "name": "1080p",
        "resolution": "1920:1080",
        "video_bitrate": "5000k",
        "audio_bitrate": "192k",
        "bandwidth": 5000000,
    },
]


def transcode_to_hls(input_path: str, output_dir: str, quality: dict):
    """
    Run FFmpeg to transcode a video to HLS format at a specific quality.
    
    HLS (HTTP Live Streaming) = video split into small .ts chunks
    + a .m3u8 playlist file that lists all the chunks in order.
    
    FFmpeg flags explained:
      -i input_path          : input file
      -vf scale=W:H          : resize video to target resolution
      -c:v libx264           : encode video with H.264 codec (most compatible)
      -b:v 2500k             : target video bitrate
      -c:a aac               : encode audio with AAC codec
      -b:a 128k              : target audio bitrate
      -hls_time 6            : each chunk is 6 seconds long
      -hls_list_size 0       : keep ALL chunks in the playlist (0 = unlimited)
      -hls_segment_filename  : naming pattern for chunk files
      -f hls                 : output format is HLS
    """
    output_playlist = os.path.join(output_dir, "index.m3u8")
    segment_pattern = os.path.join(output_dir, "segment%03d.ts")  # segment000.ts, segment001.ts, ...
    
    os.makedirs(output_dir, exist_ok=True)
    

    cmd = [
        "ffmpeg",
        "-i", input_path,
        "-vf", f"scale={quality['resolution']}",
        "-c:v", "libx264",
        "-b:v", quality["video_bitrate"],
        "-c:a", "aac",
        "-b:a", quality["audio_bitrate"],
        "-hls_time", "6",
        "-hls_list_size", "0",
        "-hls_segment_filename", segment_pattern,
        "-f", "hls",
        output_playlist,
        "-y",   # Overwrite without asking
    ]
    
    print(f"  Running FFmpeg for {quality['name']}...")
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg failed for {quality['name']}:\n{result.stderr}")
    
    print(f"  ✓ Transcoded to {quality['name']}")
    return output_playlist


def generate_thumbnail(input_path: str, output_path: str):
    """
    Extract a single frame at 2 seconds as the video thumbnail.
    FFmpeg does this with -ss (seek) and -vframes 1 (extract 1 frame).
    """
    cmd = [
        "ffmpeg",
        "-ss", "00:00:02",      # Seek to 2 seconds
        "-i", input_path,
        "-vframes", "1",         # Extract just 1 frame
        "-q:v", "2",             # JPEG quality (2 = high quality)
        "-vf", "scale=1280:720", # Resize to 720p thumbnail
        output_path,
        "-y",
    ]
    subprocess.run(cmd, capture_output=True)
    print(f"  ✓ Thumbnail generated")


def get_video_duration(input_path: str) -> int:
    """Use FFprobe (comes with FFmpeg) to get video duration in seconds."""
    cmd = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        input_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    try:
        return int(float(result.stdout.strip()))
    except:
        return 0


def create_master_playlist(video_id: str, processed_qualities: list) -> str:
    """
    Create the HLS master playlist (master.m3u8).
    
    This file tells the player what quality levels are available.
    The player (HLS.js) reads this first, then automatically picks
    the right quality based on the user's network speed.
    
    Example master.m3u8:
        #EXTM3U
        #EXT-X-VERSION:3
        
        #EXT-X-STREAM-INF:BANDWIDTH=800000,RESOLUTION=640x360,NAME="360p"
        http://localhost:9000/videos-processed/abc123/360p/index.m3u8
        
        #EXT-X-STREAM-INF:BANDWIDTH=2500000,RESOLUTION=1280x720,NAME="720p"
        http://localhost:9000/videos-processed/abc123/720p/index.m3u8
    """
    minio_public = os.getenv("MINIO_PUBLIC_URL", "http://localhost:9000")
    
    lines = ["#EXTM3U", "#EXT-X-VERSION:3", ""]
    
    for q in processed_qualities:
        w, h = q["resolution"].split(":")
        lines.append(
            f'#EXT-X-STREAM-INF:BANDWIDTH={q["bandwidth"]},'
            f'RESOLUTION={w}x{h},NAME="{q["name"]}"'
        )
        lines.append(
            f'{minio_public}/{PROCESSED_BUCKET}/{video_id}/{q["name"]}/index.m3u8'
        )
        lines.append("")
    
    return "\n".join(lines)


def process_video(job: dict):
    """
    Main processing function for a single video.
    Called for each Kafka message.
    """
    video_id = job["video_id"]
    raw_object_key = job["raw_object_key"]
    
    print(f"\n{'='*60}")
    print(f"Processing video: {video_id}")
    print(f"{'='*60}")
    
    # Create a temp folder for this video's processing
    work_dir = TMP_DIR / video_id
    work_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        # ── Step 1: Download raw video from MinIO ──────────────────────────
        print("Step 1: Downloading raw video from MinIO...")
        raw_path = str(work_dir / "original.mp4")
        download_file(RAW_BUCKET, raw_object_key, raw_path)
        
        duration = get_video_duration(raw_path)
        print(f"  Video duration: {duration} seconds")
        
        # ── Step 2: Generate thumbnail ─────────────────────────────────────
        print("Step 2: Generating thumbnail...")
        thumb_path = str(work_dir / "thumbnail.jpg")
        generate_thumbnail(raw_path, thumb_path)
        upload_file_from_disk(PROCESSED_BUCKET, f"{video_id}/thumbnail.jpg", thumb_path, "image/jpeg")
        
        # ── Step 3: Transcode to each quality level ────────────────────────
        print("Step 3: Transcoding to HLS quality levels...")
        processed_qualities = []
        
        for quality in QUALITY_LEVELS:
            output_dir = str(work_dir / quality["name"])
            
            try:
                transcode_to_hls(raw_path, output_dir, quality)
                
                # Upload all HLS files for this quality to MinIO
                for file in Path(output_dir).iterdir():
                    if file.suffix == ".m3u8":
                        content_type = "application/x-mpegURL"
                    elif file.suffix == ".ts":
                        content_type = "video/MP2T"
                    else:
                        continue
                    
                    object_name = f"{video_id}/{quality['name']}/{file.name}"
                    upload_file_from_disk(PROCESSED_BUCKET, object_name, str(file), content_type)
                
                processed_qualities.append(quality)
                
            except RuntimeError as e:
                print(f"  ⚠ Skipping {quality['name']}: {e}")
        
        if not processed_qualities:
            raise RuntimeError("All quality levels failed to transcode")
        
        # ── Step 4: Create and upload master playlist ──────────────────────
        print("Step 4: Creating master playlist...")
        master_content = create_master_playlist(video_id, processed_qualities)
        master_path = str(work_dir / "master.m3u8")
        
        with open(master_path, "w") as f:
            f.write(master_content)
        
        upload_file_from_disk(PROCESSED_BUCKET, f"{video_id}/master.m3u8", master_path, "application/x-mpegURL")
        
        # ── Step 5: Update database ────────────────────────────────────────
        print("Step 5: Updating database...")
        update_video_status(video_id, "ready", duration)
        
        print(f"\n✅ Video {video_id} is ready to stream!")
        
    except Exception as e:
        import traceback
        print(f"\n❌ Processing failed for {video_id}: {e}")
        print(traceback.format_exc())   # Shows exact line that failed
        update_video_status(video_id, "failed")
        
    finally:
        # Always clean up temp files to save disk space
        shutil.rmtree(str(work_dir), ignore_errors=True)
        print(f"✓ Cleaned up temp files for {video_id}")


def main():
    """
    Main loop: connect to Kafka, listen for jobs, process them.
    This runs forever.
    """
    print("🎬 StreamFlow Video Processor starting...")
    print(f"   Kafka: {KAFKA_SERVERS}")
    print(f"   Topic: {TOPIC}")
    
    # Wait for Kafka to be fully ready (sometimes takes a moment after startup)
    time.sleep(10)
    
    # Configure Kafka consumer
    consumer = Consumer({
        "bootstrap.servers": KAFKA_SERVERS,
        "group.id": "video-processors",
        # group.id is important: if you run 3 processor containers,
        # Kafka automatically distributes jobs between them (load balancing!)
        "auto.offset.reset": "earliest",
        # "earliest" = if we restart, process any jobs we missed
    })
    
    consumer.subscribe([TOPIC])
    print(f"✓ Listening for jobs on topic: {TOPIC}")
    
    try:
        while True:
            # Poll for a message (wait up to 1 second)
            msg = consumer.poll(timeout=1.0)
            
            if msg is None:
                continue   # No message, keep waiting
            
            if msg.error():
                # Only raise if it's NOT a topic-not-ready error
                if msg.error().code() == KafkaError.UNKNOWN_TOPIC_OR_PART:
                    print("Topic not ready yet, retrying in 5 seconds...")
                    time.sleep(5)
                    continue
                raise KafkaException(msg.error())
            # Parse the job message
            job = json.loads(msg.value().decode("utf-8"))
            
            try:
                process_video(job)
            except Exception as e:
                print(f"❌ Failed to process job: {e}")
                # In production you'd send this to a dead-letter queue
                # For now, we just log and continue
    
    except KeyboardInterrupt:
        print("Shutting down processor...")
    finally:
        consumer.close()


if __name__ == "__main__":
    main()