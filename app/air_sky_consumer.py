from kafka import KafkaConsumer
import json
import boto3
import io

def safe_json_loads(value):
    try:
        if not value:
            return None
        return json.loads(value.decode("utf-8"))
    except Exception as e:
        print(f"⚠️ Skipping invalid message: {e}")
        return None

consumer = KafkaConsumer(
    "test-topic",
    bootstrap_servers=["kafka:9092"],
    auto_offset_reset="earliest",
    enable_auto_commit=True,
    value_deserializer=safe_json_loads,
)

def main():
    s3 = boto3.client(
        "s3",
        endpoint_url="http://minio:9000",
        aws_access_key_id="minioadmin",
        aws_secret_access_key="minioadmin",
    )
    bucket = "datalake"

    for message in consumer:
        data = message.value
        if not data:
            continue  # skip empty or invalid messages

        # Create an in-memory buffer
        json_bytes = io.BytesIO(json.dumps(data).encode("utf-8"))
        key = f"opensky_{message.timestamp}.json"

        s3.upload_fileobj(json_bytes, bucket, key)
        print(f"✅ Saved {key} to MinIO")

if __name__ == "__main__":
    main()
