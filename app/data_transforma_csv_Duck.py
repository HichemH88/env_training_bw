from airflow import DAG
from airflow.providers.docker.operators.docker import DockerOperator
from docker.types import Mount
from datetime import datetime

with DAG(
    dag_id="data_silver_csv_duckdb",
    start_date=datetime(2025, 9, 2),
    schedule_interval=None,  # manual run; or use a cron schedule
    catchup=False,
    tags=["minio", "duckdb"],
) as dag:

    run_duckdb_transform = DockerOperator(
        task_id="silver_layer_csv_duckdb",
        image="env_training-python-app-demo:python_test",  # replace with your Python container image
        api_version="auto",
        auto_remove=True,
        entrypoint="",
        command=['python', '/app/app/extract_csv_data.py'],
        docker_url="unix://var/run/docker.sock",  # Docker socket must be mounted
        network_mode="data-network",  # or your shared network if MinIO is in another container
        mount_tmp_dir=False,
        mounts=[
        Mount(
            target="/app/app",  # inside the container
            source="C:/Users/biwar/Documents/scripts",  # your Windows host path
            type="bind"
        )
    ],
    )
    
    