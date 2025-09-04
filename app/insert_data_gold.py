import duckdb
from minio import Minio
import pandas as pd
from sqlalchemy import create_engine



# ===== 1. MinIO Config =====
MINIO_ENDPOINT = "minio:9000"  # "localhost:9000" if outside Docker
MINIO_ACCESS_KEY = "minioadmin"
MINIO_SECRET_KEY = "minioadmin"
BRONZE_BUCKET = "datalake"
SILVER_BUCKET = "silver/orders"
PARQUET_FILE = "silver_customers_bank.parquet"  # Your raw CSV in MinIO

# ===== 2. Initialize Clients =====
minio_client = Minio(
    MINIO_ENDPOINT,
    access_key=MINIO_ACCESS_KEY,
    secret_key=MINIO_SECRET_KEY,
    secure=False
)

conn = duckdb.connect()

# Enable S3 extensions
conn.execute("INSTALL httpfs; LOAD httpfs;")
conn.execute(f"""
    SET s3_endpoint='{MINIO_ENDPOINT}';
    SET s3_access_key_id='{MINIO_ACCESS_KEY}';
    SET s3_secret_access_key='{MINIO_SECRET_KEY}';
    SET s3_use_ssl=false;
    SET s3_url_style='path';
""")

# ===== 3. Read parquet from MinIO (Bronze Layer) =====
conn.execute(f"""
    CREATE TEMPORARY TABLE temp_customers_bank AS
    SELECT * FROM read_parquet(
        's3://{SILVER_BUCKET}/{PARQUET_FILE}',
        hive_partitioning=false
    );
""")

# ===== 4. Transform Data (Silver Layer) =====
conn.execute(f"""
    CREATE TEMPORARY TABLE gold_customers_bank AS
    SELECT
        *
    FROM temp_customers_bank ;
""")


# ===== 6. Store Metadata in DuckDB =====
conn.execute(f"""
    CREATE OR REPLACE VIEW gold_cust_bank_metadata AS
    SELECT 
        column_name, 
        data_type 
    FROM information_schema.columns 
    WHERE table_name = 'gold_customers_bank';
""")

# ===== 7. Log Results =====
print("=== Bronze → Silver Pipeline Complete ===")

print("\n=== Schema ===")
print(conn.sql("SELECT * FROM gold_cust_bank_metadata").df())
print(conn.sql("SELECT count(*) FROM gold_customers_bank").df())
print(conn.sql("SELECT * FROM gold_customers_bank limit 20").df())
df = conn.execute("SELECT * FROM gold_customers_bank").df()
print(f"Loaded {len(df)} rows from DuckDB")
print("Columns:", df.columns.tolist())

engine = create_engine('postgresql://admin:admin@172.26.0.4:5432/mydb')
schema_name = 'dev'
df.to_sql('gold_customers_bank', engine, if_exists='replace', index=False)
print(f"Data successfully loaded into PostgreSQL schema '{schema_name}'!")
conn.close()