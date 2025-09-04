from airflow import DAG
from airflow.providers.docker.operators.docker import DockerOperator
from docker.types import Mount
from datetime import datetime

with DAG(
    dag_id="duckdb_minio_pipeline",
    start_date=datetime(2025, 8, 19),
    schedule_interval=None,  # manual run; or use a cron schedule
    catchup=False,
    tags=["duckdb", "minio"],
) as dag:

   run_duckdb_transform = DockerOperator(
    task_id="run_duckdb_silver",
    image="env_training-python-app-demo",
    api_version="auto",
    auto_remove=True,
    entrypoint="",
    command=['python', '/app/app/data_transform_minio_duckdb.py'],
    docker_url="unix://var/run/docker.sock",
    network_mode="data-network",
    mount_tmp_dir=False,
    mounts=[
        Mount(
            target="/app/app",  # inside the container
            source="C:/Users/biwar/Documents/scripts",  # your Windows host path
            type="bind"
        )
    ],
)
    
    