import os
from minio import Minio
import io

endpoint = os.getenv("MINIO_ENDPOINT","http://minio:9000").replace("http://","").replace("https://","")
is_secure = os.getenv("MINIO_ENDPOINT","").startswith("https://")

minio_client = Minio(
    endpoint=endpoint,
    access_key=os.getenv("MINIO_ROOT_USER","minioadmin"),
    secret_key=os.getenv("MINIO_ROOT_PASSWORD","minioadmin"),
    secure=is_secure
)

RAW_BUCKET = "videos-raw"
PROCESSED_BUCKET = "videos-processed"

def download_file(bucket: str, object_name: str, dest_path: str):
    minio_client.fget_object(
        bucket_name=bucket,
        object_name=object_name,
        file_path=dest_path,
    )
    print(f"Downloaded from MINIO: {bucket}/{object_name} -> {dest_path}")

def upload_file_from_disk(bucket: str, object_name: str, file_path: str, content_type: str):
    minio_client.fput_object(
        bucket_name=bucket,
        object_name=object_name,
        file_path=file_path,
        content_type=content_type,
    )
    print(f"Uploaded file {bucket}/{object_name} {file_path}")
