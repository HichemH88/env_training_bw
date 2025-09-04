import duckdb
import re

def load_minio_tables_separately():
    """Load each CSV file from MinIO as a separate table"""
    
    con = duckdb.connect()
   # Use a persistent database file
    con = duckdb.connect('/app/my_data.duckdb')  # This will persist the data 
    # Load and configure HTTPFS
    con.execute("INSTALL httpfs;")
    con.execute("LOAD httpfs;")
    
    # MinIO configuration
    MINIO_ENDPOINT = "minio:9000"
    MINIO_ACCESS_KEY = "minioadmin"
    MINIO_SECRET_KEY = "minioadmin"
    BUCKET_NAME = "datalake"
    
    # Set MinIO configuration
    con.execute(f"SET s3_endpoint='{MINIO_ENDPOINT}';")
    con.execute(f"SET s3_access_key_id='{MINIO_ACCESS_KEY}';")
    con.execute(f"SET s3_secret_access_key='{MINIO_SECRET_KEY}';")
    con.execute("SET s3_use_ssl=false;")
    con.execute("SET s3_url_style='path';")
    
    # Construct S3 path
    s3_path = f"s3://{BUCKET_NAME}/"
    
    print(f"Looking for CSV files in: {s3_path}")
    
    # CORRECTED: Use 'file' instead of 'name'
    files_result = con.execute(f"""
        SELECT file FROM glob('{s3_path}*.csv')
    """).fetchall()
    
    csv_files = [f[0] for f in files_result]
    print(f"Found {len(csv_files)} CSV files in MinIO")
    
    # Load each file as separate table
    for file_path in csv_files:
        try:
            # Extract table name from file path
            file_name = file_path.split('/')[-1]
            table_name = re.sub(r'[^a-zA-Z0-9_]', '_', file_name.split('.')[0])
            
            # Ensure valid table name
            if not table_name[0].isalpha():
                table_name = 't_' + table_name
            
            print(f"Loading {file_name} as table '{table_name}'...")
            
            # Create table from MinIO CSV
            con.execute(f"""
                CREATE OR REPLACE TABLE {table_name} AS 
                SELECT * FROM read_csv('{file_path}', 
                    auto_detect=true,
                    header=true
                )
            """)
            
            # Get row count
            count = con.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
            print(f"  → Successfully loaded {count} rows")
            
        except Exception as e:
            print(f"  → Error loading {file_path}: {str(e)}")
    
    return con, csv_files
print("✅ Data loaded to persistent database: my_data.duckdb")
# Usage
con, loaded_files = load_minio_tables_separately()
def list_all_tables_metadata(con):
    """List all tables with their column metadata"""
    
    # Get all tables
    tables = con.execute("SHOW TABLES").fetchall()
    
    print("=" * 80)
    print("DATABASE METADATA OVERVIEW")
    print("=" * 80)
    
    for table in tables:
        table_name = table[0]
        print(f"\n📊 TABLE: {table_name}")
        print("-" * 50)
        
        # Get table schema
        schema = con.execute(f"DESCRIBE {table_name}").fetchall()
        
        # Get row count
        row_count = con.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
        print(f"Rows: {row_count:,}")
        
        # Print column details
        print("\nColumns:")
        for col in schema:
            col_name, col_type, null_flag, key_flag, default_val, extra = col
            print(f"  • {col_name}: {col_type} {'(NULL)' if null_flag == 'YES' else '(NOT NULL)'}")
    
    return tables

# Usage
tables = list_all_tables_metadata(con)