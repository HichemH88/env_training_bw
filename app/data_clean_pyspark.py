from pyspark.sql import SparkSession
from pyspark.sql.functions import col, when, lit, udf, count, isnull, sum as _sum, mean, stddev
from pyspark.sql.types import BooleanType
from datetime import datetime
import psycopg2
import sys

# Initialize Spark Session with PostgreSQL JDBC
spark = SparkSession.builder \
    .appName("data quality check") \
    .config("spark.driver.extraClassPath", "/opt/spark/jars/postgresql-42.7.7.jar") \
    .config("spark.executor.extraClassPath", "/opt/spark/jars/postgresql-42.7.7.jar") \
    .getOrCreate()

def check_control_table():
    """Check if the staging job completed successfully"""
    try:
        conn = psycopg2.connect(
            host="db-demo",
            database="mydb",
            user="admin",
            password="admin"
        )
        cursor = conn.cursor()
        
        print("Checking control table for recent successful runs...")
        
        cursor.execute("""
            SELECT flag, rows_processed, start_time 
            FROM dev.control_table 
            WHERE process_name = 'PostgreSQL CSV Load'
            AND flag = 'True'
            AND start_time > NOW() - INTERVAL '24 HOURS'
            ORDER BY start_time DESC 
            LIMIT 1
        """)
        
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if result:
            print(f"Found successful run at {result[2]} with {result[1]} rows processed")
            return True
        else:
            print("No successful runs found in last 24 hours")
            return False
            
    except Exception as e:
        print(f"ERROR checking control table: {str(e)}")
        return False

# Main execution flow
if check_control_table():
    print("Proceeding with data quality checks...")
    
    # PostgreSQL connection parameters
    db_url = "jdbc:postgresql://db-demo/mydb"
    properties = {
        "user": "admin",
        "password": "admin",
        "driver": "org.postgresql.Driver"
    }

    # Read data from PostgreSQL
    table_name = "dev.bronze_sales"
    df = spark.read.jdbc(url=db_url, table=table_name, properties=properties, numPartitions=10)

    # DATA QUALITY CHECKS
def is_valid_time(time_str):
    """Check if timestamp matches expected format"""
    try:
        datetime.strptime(str(time_str), "%Y-%m-%d %H:%M:%S")  # Handle None/null
        return True
    except (ValueError, TypeError):
        return False

# Register UDF for time validation
time_validator = udf(is_valid_time, BooleanType())  # Note: 'time_validator' is now the callable UDF

# 1. NULL CHECK
null_checks = df.select(
    [count(when(isnull(c), c)).alias(c) for c in df.columns]
)
print("=== NULL VALUE COUNTS ===")
#null_checks.show(10)

# 2. PRICE VALIDATION
price_stats = df.select(
    mean("price").alias("avg_price"),
    stddev("price").alias("stddev_price")
).collect()[0]

price_threshold = price_stats["avg_price"] + 3 * price_stats["stddev_price"]

invalid_prices = df.filter(
    (col("price") <= 0) | 
    (col("price") > price_threshold)
)
print(f"\n=== INVALID PRICES (>{price_threshold:.2f} or <=0) ===")
invalid_prices.show()

# 3. brand CONSISTENCY
valid_categories =  "'sony', 'samsung', 'xiaomi', 'huawei'"  # Modify as needed
invalid_categories = df.filter(~col("brand").isin(valid_categories))
print("\n=== INVALID CATEGORIES ===")
invalid_categories.select("brand").distinct().show()

# 4. TIME FORMAT VALIDATION
invalid_times = df.filter(~time_validator(col("event_time")))
print("\n=== INVALID TIME FORMATS ===")
invalid_times.select("event_time").show(truncate=False)


# 5. BASIC STATISTICS
print("\n=== BASIC STATISTICS ===")
df.describe(["price"]).show()

# ======================
# DATA CLEANING SUGGESTIONS
# ======================
print("\n=== DATA CLEANING RECOMMENDATIONS ===")

# If nulls found in product/category
if null_checks.select(_sum("product_id")).collect()[0][0] > 0:
    print("ACTION: Handle null values in 'product' column (impute or remove rows)")

if null_checks.select(_sum("brand")).collect()[0][0] > 0:
    print("ACTION: Replace null categories with 'unknown' category")

if invalid_prices.count() > 0:
    print(f"ACTION: Investigate {invalid_prices.count()} invalid price entries")

if invalid_categories.count() > 0:
    print(f"ACTION: Standardize {invalid_categories.count()} invalid categories")

if invalid_times.count() > 0:
    print(f"ACTION: Fix {invalid_times.count()} malformed timestamps")

    # Write issues to Parquet
    df.createOrReplaceTempView("data")
 
    issues_df = spark.sql(f"""
        SELECT price, brand, product_id,
               CASE WHEN price <= 0 THEN 'Invalid price'
                    WHEN price > {price_threshold} THEN 'Invalid price'
                    WHEN brand NOT IN {tuple(valid_categories)} THEN 'Invalid brand'
                    ELSE 'Valid'
               END AS issue_type
        FROM data
    """)
    print("✅ Result of issues_df (data quality flags):")
    issues_df.show(truncate=False)
    issues_df.write.mode("overwrite").parquet("/tmp/data_issues/")
     # PostgreSQL connection parameters
    db_url = "jdbc:postgresql://db-demo/mydb"
    properties = {
        "user": "admin",
        "password": "admin",
        "driver": "org.postgresql.Driver"
    }
    table_name = "dev.data_issues"
    issues_df.write \
    .mode("overwrite") \
    .jdbc(url=db_url, table=table_name, properties=properties)
#else:
#    print("Data quality checks aborted - no successful data load detected")
#    sys.exit(1)

spark.stop()