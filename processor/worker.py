import os
import json
import shutil
import subprocess
import time
from pathlib import Path
from confluent_kafka import Consumer, kafkaException

from storage import download_file,upload_file_from_disk, RAW_BUCKET, PROCESSED_BUCKET
from database import update_video_status

KAFKA_SERVER = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:29092")
TOPIC = "video-processing-jobs"
TMP_DIR = Path("/tmp/processing")

QUALITY_LEVELS = [
    {
        "name": "360p",
        "resolution": "640x360",
        "bitrate": "800k",
        "audio_bitrate": "96k",
        "bandwidth": 8000000
    },
    {
        "name": "480p",
        "resolution": "854x480",
        "bitrate": "1200k",
        "audio_bitrate": "128k",
        "bandwidth": 25000000
    },
    {
        "name": "720p",
        "resolution": "1280x720",
        "bitrate": "2500k",
        "audio_bitrate": "192k",
        "bandwidth": 50000000
    }
]


def transcode_to_hls(input_path: str, output_dir: str,quality: dict):
    output_playlist = os.path.join(output_dir,"index.m3u8")
    segment_pattern = os.path.join(output_dir,"segment_%03d.ts")

    cmd = [
        "ffmpeg",
        "-i", input_path,
        "-c:v", "libx264",
        "-b:v", f"scale={quality['resolution']}",
        "-c:a", "aac",
        "-b:a", quality["audio_bitrate"],
        "-hls_time", "6",
        "-hls_list_size", "0",
        "-hls_segement_filename", segment_pattern,
        "-f","hls",
        output_playlist,
        "-y",
    ]

    print(f"Running ffmpeg for {quality['name']}....")
    result = subprocess.run(cmd, capture_output=True,text=True)

if result.returncode != 0:
    raise RuntimeError(f"ffmpeg failed for {quality['name']}: \n {result.stderr}")

print(f"ffmpeg completed for {quality['name']}")

return output_playlist


def generate_thumbnail(input_path: str, output_path: str):

    cmd = [
        "ffmpeg",
        "-ss", "00:00:02",
        "-i", input_path,
        "-vframes", "1",
        "-q:v", "2",
        "-vf", "scale=1280:720",
        output_path,
        "-y",

    ]
    subprocess.run(cmd,capture_output=True)

    print(f"Thumbnail generated at {output_path}")

def get_video_duration(input_path: str)->int:
    cmd = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format-duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        input_path,
    ]

    result = subprocess.run(cmd,capture_output=True,text=True)
    try:
        return int(float(result.stdout.strip()))
    except:
        return 0


def create_master_playlist(video_id: str, processed_qualities: list) -> str:
    minio_public = os.getenv("MINIO_PUBLIC_URL","http://localhost:9000")

    lines = ["#EXTM3U", "#EXT-X-VERSION:3", ""]

    for q in processed_qualities:
        w,h = q["resolution"].split(":")
        lines.appen(
            f'#EXT-X-STREAM-INF:BANDWIDTH={q["bandwidth"]},'
            f'RESOLUTION={w}x{h},NAME="{q["name"]}"'
            )
        lines.append(
            f"{minio_public}/{PROCESSED_BUCKET}/{video_id}/{q["name"]}/index.m3u8"
        )

        lines.append("")

    return "\n".join(lines)


def process_video(job: dict):
    video_id = joib["video_id"]
    raw_object_key=job["raw_object_key"]

    print(f"\n{'='*60}")
    print(f"Processing video {video_id} from {raw_object_key}")
    print(f"{'='*60}\n")

    work_dir = TMP_DIR / video_id
    work_dir.mkdir(parents=True, exist_ok=True)

    try:
        print("Step 1: Downloading video from Minio...")
        raw_path = str(work_dir/"original.mp4")
        download_file(RAW_BUCKET,raw_object_key,raw_path)

        duration = get_video_duration(raw_path)
        print(f"Video duration: {duration} seconds")

        print("Step 2: Generating thumbnail...")
        thumb_path = str(work_dir/"thumbnail.jpg")
        generate_thumbnail(raw_path,thumb_path)
        upload_file_from_disk(PROCESSED_BUCKET,f"{video_id}/thumbnail.jpg",thumb_path,"image/jpeg")

        print("Step 3: Transcoding to HLS quality levels...")
        processed_qualities = []

        for quality in QUALITY_LEVELS:
            output_dir = str(work_dir/quality["name"])

            try:
                transcode_to_hls(raw_path,output_dir,quality)

                for file in Path(output_dir).iterdir():
                    if file.suffix == ".m3u8":
                        content_type = "application/x-mpegURL"
                    elif file.suffix == ".ts":
                        content_type = "video/MP2T"
                    else:
                        continue
                    
                    object_name = f"{video_id}/{quality['name']}/{file.name}"
                    upload_file_from_disk(PROCESSED_BUCKET,object_name,str(file),content_type)
                processed_qualities.append(quality)
            except RuntimeError as e:
                rasie RuntimeError(f"Skipping quality {quality}: {e}")

        
        if not processed_qualities:
            raise RuntimeError("All quality levels failed to transcode")
        
        print("Step 4: Creating master playlist..." )

        master_content = create_master_playlist(video_id,processed_qualities)
        master_path = str(work_dir/"master.m3u8")


        with open(master_path, "w") as f:
            f.write(master_content)
        
        upload_file_from_disk(PROCESSED_BUCKET,f"{video_id}/master.m3u8",master_path,"application/x-mpegURL")

        print("Step 5: updating database")
        update_video_status(video_id,"ready",duration)

        print(
            f"Video processing completed successfully ready strem!"
        )
    
    except Exception as e:
        pritn(f"\n Processing failed: {video_id}: {e}")
        update_video_status(video_id,"failed")
        raise
    finally:
        shutil.rmtree(str(work_dir),ignore_errors=True)
        print(f"Cleaned up worker directory: {video_id}")
    

def main():

    print("🎬 StreamFlow Video Processor starting...")
    print(f"   Kafka: {KAFKA_SERVERS}")
    print(f"   Topic: {TOPIC}")

    time.sleep(10)

    consumer = Consumer({
        "bootstrap.servers": KAFKA_SERVER,
        "group.id": "video-processors",
        "auto.offset.reset": "earliest",
    })

    consumer.subscribe([TOPIC])

    print("Waiting for video processing jobs... Listening...[{TOPIC}]")

    try:
        while True:
            msg  = consumer.poll(timeout=1.0)

            if msg in None:
                continue
            
            if msg.error():
                raise KafkaException(msg.error())
            
            job = json.loads(msg.value().decode("utf-8"))

            try:
                process_video(job)
            except Exception as e:
                print(f"❌ Failed to process job: {e}")
    except KeyboardInterrupt:
        print("Shutting down processor...")
    finally:
        consumer.close()



if __name__ == "__main__":
    main()