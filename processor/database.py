import os
import psycopg2
from psycopg2.extras import RealDictCursor

def get_connection():
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST","postgres"),
        database=os.getenv("POSTGRES_DB","streamflow"),
        user=os.getenv("POSTGRES_USER","streamflow"),
        password=os.getenv("POSTGRES_PASSWORD","streamflow123"),
        port=os.getenv("POSTGRES_PORT","5432"),
        cursor_factory=RealDictCursor,
    )

def update_video_status(video_id: str, status: str, duration: int = None):
    conn = get_connection()
    try: 
        with conn.cursor() as cur:
            if duration:
                cur.execute(
                    """
                    UPDATE videos
                    SET status = %s, duration_seconds= %s, updated_at=NOW()
                    WHERE id = %s
                    """,
                    (status,duration,video_id)
                )
            else:
                cur.execute(
                    "UPDATE videos SET status=%s ,updated_at = NOW(), WHERE id = %s",
                    (status,video_id)
                )
            
        conn.commit()
        print(f"Database updated: video{video_id} -> {status}")

    finally:
        conn.close()
      