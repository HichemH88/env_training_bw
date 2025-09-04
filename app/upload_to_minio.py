from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from airflow.operators.trigger_dagrun import TriggerDagRunOperator
from datetime import datetime
import boto3
import os

def upload_to_minio():
    minio_url = "http://minio:9000"  # inside Docker network
    access_key = "minioadmin"
    secret_key = "minioadmin"
    bucket_name = "datalake"
    local_folder = "/opt/airflow/data"

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
        if file.endswith(".csv"):
            file_path = os.path.join(local_folder, file)
            s3.upload_file(file_path, bucket_name, file)
            print(f"✅ Uploaded: {file} → {bucket_name}")

default_args = {
    'owner': 'airflow',
    'start_date': datetime(2025, 7, 23),
    'retries': 0,
}

with DAG(
    dag_id='upload_csv_to_minio',
    default_args=default_args,
    schedule_interval='@daily',
    catchup=False,
    tags=["minio", "csv", "upload"],
) as dag:

    upload_task = PythonOperator(
        task_id='upload_csv_files_toMinio',
        python_callable=upload_to_minio,
    )
    trigger_duckdb_dag = TriggerDagRunOperator(
        task_id="run_duckdb_silver",
        trigger_dag_id="duckdb_minio_pipeline",  # This is DAG2
        wait_for_completion=True
    )
    trigger_PG_dag = TriggerDagRunOperator(
        task_id="gold_layer_PG",
        trigger_dag_id="duckdb_PG_pipeline",  # This is DAG2
        wait_for_completion=True
    )

    upload_task >>  trigger_duckdb_dag >> trigger_PG_dag