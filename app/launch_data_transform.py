from airflow import DAG
from airflow.providers.docker.operators.docker import DockerOperator
from datetime import datetime

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2025, 1, 18),
}

with DAG('python_container_dag', default_args=default_args, schedule_interval=None) as dag:
    docker_task = DockerOperator(
        task_id='python-app-demo',
        image='env_training-python-app-demo',
        api_version='auto',
        auto_remove=True,
        command='python /app/data_transform_minio_duckdb.py',
        docker_url='unix:///var/run/docker.sock',
        network_mode='data-network',
        mounts=[
            # Mount any volumes needed
             '/data/inputs:/mnt/inputs:ro',
             '/data/outputs:/mnt/outputs',
        ]
    )