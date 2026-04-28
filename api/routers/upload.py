import uuid
import os
from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from database import get_db
from storage import upload_file, RAW_BUCKET
from kafka_producer import send_video_job

router = APIRouter()

MAX_FILE_SIZE = 500*1024*1024

ALLOWED_TYPES = {
    "video/mp4", "video/mpeg", "video/quicktime",
    "video/x-msvideo", "video/webm","video/mkv"
}

@router.post("/")
async def upload_video(
    file: UploadFile = File(..., description="Video file to upload"),
    title: str = Form(..., description="Video title"),
    description: str = Form("", description="Video Description"),
    db: AsyncSession = Depends(get_db)
)

if file.content_type not in ALLOWED_TYPES:
    raise HTTPException(
        status_code=400,
        detail=f"Invalid file type: {file.content_type}, ALLOWED: {ALLOWED_TYPES}"
    )

content = await file.read()

if len(content) > MAX_FILE_SIZE:
    raise HTTPException(
        status_code=413,
        detial=f"File too large. Maximum size is 500MB."
    )

video_id = str(uuid.uuid4())

original_filename = file.filename or "video.mp4"
extension = os.path.splitext(original_name)[1] or ".mp4"

raw_object_key = f"{video_id}/original{extension}"

upload_file(
    bucket = RAW_BUCKET,
    object_name=raw_object_key,
    data=content,
    content_type=file.content_type
)


print("RAW video uploaded to Minio: {raw_object_key}")

await db.execute(
    text("""
        INSERT INTO videos (id,title,description, status, original_filename, file_size_bytes)
        VALUES (:id, :title, :description, 'processing', :filename, :size)
    """),
    {
        "id": video_id,
        "title": title,
        "description": description,
        "filename": original_filename,
        "size": len(content),
    }
)

await db.commit()

print(f"Video record created in database: {video_id}")


send_video_job(
    video_id=video_id,
    raw_object_key=raw_object_key,
    title=title,
)


return {
    "video_id": video_id,
    "title": title,
    "status": "processing",
    "message": "Video uploaded; Transcoading started Check status at /api/videos/{video_id}",
}