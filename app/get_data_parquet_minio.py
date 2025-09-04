from fastapi import FastAPI, Query
import duckdb
import os
from minio import Minio

# ===== 1. MinIO Configuration =====
MINIO_ENDPOINT = "172.26.0.2:9000"  # Use "minio:9000" if running inside Docker
MINIO_ACCESS_KEY = "minioadmin"
MINIO_SECRET_KEY = "minioadmin"
MINIO_BUCKET = "datalake"
PARQUET_FILE = "weather.parquet"

def query_minio():
    conn = duckdb.connect()
    
    # 1. Setup S3 access
    conn.execute("INSTALL httpfs; LOAD httpfs;")
    conn.execute(f"""
        SET s3_endpoint='{MINIO_ENDPOINT}';
        SET s3_access_key_id='minioadmin';
        SET s3_secret_access_key='minioadmin';
        SET s3_url_style='path';
        SET s3_use_ssl=false;
    """)
    
    # 2. Execute query
    query = f"""
        SELECT * 
        FROM read_parquet('s3://{MINIO_BUCKET}/{PARQUET_FILE}')
        LIMIT 10;
    """
    return conn.sql(query).df()

if __name__ == "__main__":
    df = query_minio()
    print(df)
    # ===== Allow standalone run =====
