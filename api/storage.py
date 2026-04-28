import os
from minio import Minio
from minio.error import S3Error
import io


endpoint = os.getenv("MINIO_ENDPOINT", "https://minio:9000").replace("http://","").replace("https://","")
is_secure = os.getenv("MINIO_ENDPOINT","").startswith("https://")

minio_client = Minio(
    endpoint = endpoint,
    access_key=os.getenv("MINIO_ROOT_USER","minioadmin"),
    secret_key=os.getenv("MINIO_ROOT_PASSWORD","minioadmin"),
    secure=is_secure,
)

RAW_BUCKET = "videos-raw"
PROCESSED_BUCKET="videos-processed"

def init_buckets():
    for bucket in [RAW_BUCKET, PROCESSED_BUCKET]:
        if not minio_client.bucket_exists(bucket):
            minio_client.make_bucket(bucket)
            print(f"Created bucket: {bucket}")
        else:
            print(f"bucket exists: {bucket}")
        
    public_policy = """{
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Principal": {"AWS": ["*"]},
            "Action": ["s3:GetObject"],
            "Resource": ["arn:aws:s3:::videos-processed/*"]
        }]
    }"""

    minio_client.set_bucket_policy(PROCESSED_BUCKET,public_policy)
    print("Set videos-processsed bucket to public")


def upload_file(bucket: str, object_name: str, data: bytes, content_type: str):
    minio_client.put_object(
        bucket_name=bucket,
        object_name=object_name,
        data=io.BytesIO(data),
        length=len(data),
        content_type=content_type
    )
    public_url=os.getenv("MINIO_PUBLIC_URL","http://localhost:9000")
    return f"{public_url}/{bucket}/{object_name}"

def get_file_url(bucket: str, object_name: str):

    public_url= os.getenv("MINIO_PUBLIC_URL","http://localhost:9000")
    return f"{public_url}/{bucket}/{object_name}"

