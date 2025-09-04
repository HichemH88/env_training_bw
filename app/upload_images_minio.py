from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime
import boto3
import os

def upload_to_minio():
    minio_url = "http://172.26.0.2:9000"  # inside Docker network
    access_key = "minioadmin"
    secret_key = "minioadmin"
    bucket_name = "datalake"
    local_folder = "/tmp/Screenshots"

    s3 = boto3.client(
        "s3",
        endpoint_url=minio_url,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key
    )

    # Ensure bucket exists
    buckets = [b["Name"] for b in s3.list_buckets()["Buckets"]]
    if bucket_name not in buckets:
        s3.create_bucket(Bucket=bucket_name)

    # Upload CSV files
    for file in os.listdir(local_folder):
        if file.endswith(".png"):
            file_path = os.path.join(local_folder, file)
            s3.upload_file(file_path, bucket_name, file)
            print(f"✅ Uploaded: {file} → {bucket_name}")

default_args = {
    'owner': 'airflow',
    'start_date': datetime(2025, 8, 11),
    'retries': 0,
}

with DAG(
    dag_id='upload_images_to_minio',
    default_args=default_args,
    schedule_interval='@hourly',
    catchup=False,
    tags=["minio", "png", "upload"],
) as dag:

    upload_task = PythonOperator(
        task_id='upload_images_files',
        python_callable=upload_to_minio,
    )
