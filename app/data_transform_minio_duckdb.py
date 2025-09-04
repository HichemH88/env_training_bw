import duckdb
from minio import Minio

# ===== 1. MinIO Config =====
MINIO_ENDPOINT = "minio:9000"  # "localhost:9000" if outside Docker
MINIO_ACCESS_KEY = "minioadmin"
MINIO_SECRET_KEY = "minioadmin"
BRONZE_BUCKET = "datalake"
SILVER_BUCKET = "silver"
CSV_FILE = "bank_customers.csv"  # Your raw CSV in MinIO

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

# ===== 3. Read CSV from MinIO (Bronze Layer) =====
conn.execute(f"""
    CREATE or replace  TABLE customers_bank AS
    SELECT * FROM read_csv(
        's3://{BRONZE_BUCKET}/{CSV_FILE}',
        header=True,
        delim=','
    );
""")

# ===== 4. Transform Data (Silver Layer) =====
conn.execute(f"""
    CREATE TEMPORARY TABLE silver_customers_bank AS
    SELECT
        *
    FROM customers_bank where ACCT_TYPE='SAV';
""")
# ===== 6. Verify the silver data =====
print("\n=== Silver data verification ===")
print("Row count in silver table:")
row_count = conn.sql("SELECT COUNT(*) FROM silver_customers_bank").df()
print(row_count)
# ===== 5. Write to MinIO as Parquet (Silver Layer) =====
conn.execute(f"""
    COPY silver_customers_bank 
    TO 's3://{SILVER_BUCKET}/orders/silver_customers_bank.parquet'
    WITH (FORMAT 'parquet');
""")

# ===== 6. Store Metadata in DuckDB =====
conn.execute(f"""
    CREATE OR REPLACE VIEW silver_cust_bank_metadata AS
    SELECT 
        column_name, 
        data_type 
    FROM information_schema.columns 
    WHERE table_name = 'silver_customers_bank';
""")

# ===== 7. Log Results =====
print("=== Bronze → Silver Pipeline Complete ===")
print(f"Bronze CSV: s3://{BRONZE_BUCKET}/{CSV_FILE}")
print(f"Silver Parquet: s3://{SILVER_BUCKET}/cust/silver_customers_bank.parquet")
print("\n=== Schema ===")
print(conn.sql("SELECT * FROM silver_cust_bank_metadata").df())
try:
    # Get results as a list
    result = conn.execute("SELECT distinct ACCT_TYPE FROM silver_customers_bank").fetchall()
    print("Account types:")
    for row in result:
        print(f"  - {row[0]}")
        
except Exception as e:
    print(f"DuckDB error: {e}")
