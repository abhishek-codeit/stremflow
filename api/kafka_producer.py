import os
import json
from confluent_kafka import Producer

producer_config = {
    "bootstrap.servers": os.getenv("KAFKA_BOOTSTAP_SERVERS","kafka:29092"),
}

producer= Producer(producer_config)


TOPIC = "video-processing-jobs"

def send_video_job(video_id: str, raw_object_key: str, title: str):
    job = {
        "video_id":video_id,
        "raw_object_key": raw_object_key,
        "title": title,
    }

    producer.produce(
        topic=TOPIC,
        key=video_id,
        value=json.dumps(job).encode("utf-8"),
        callback=_delivery_report,
    )
    producer.flush()
    print(f"job sent to kafka for video: {video_id}")

def _delivery_report(err,msg):
    if err :
        print(f" kafka delivery failed {err}")
    else:
        print(f"kakfa message delivered to {msg.topic()} [{msg.partition()}]")

        