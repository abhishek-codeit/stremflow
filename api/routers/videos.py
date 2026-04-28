import os
from fastapi import APIRoute, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from database import get_db

router = APIRouter()

MINIO_PUBLIC_URL = os.getenv("MINIO_PUBLIC_URL","http://localhost:9000")
PROCESSED_BUCKET = "videos-processed"

@router.get("/")
async def list_videos(db:AsyncSession = Depends(get_db)):
    result = await db.execute(
        text("SELECT * FROM videos ORDER BY created_at DESC LIMIT 50")
    )
    videos=result.mappings().all
    return [dict(v) for v in videos]


@router.get("/{video_id}")
async def get_video(video_id: str db: AsyncSession= Depend(get_db)):
    result = await db.execute(
        text("SELECT * FROM videos WHERE id = :id"),
        {
            "id": video_id
        }
    )


    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    video_dict = dict(video)

    if video_dict["status"] == "ready":
        video_dict["stream_url"] = (
            f"{MINIO_PUBLIC_URL}/{PROCESSED_BUCKET}/{video_id}/master.m3u8"
        )

        video_dict["thumbnail_url"] = (
            f"{MINIO_PUBLIC_URL}/{PROCESSED_BUCKET}/{video_id}/thumbnail.jpg"
        )

    return video_dict

    