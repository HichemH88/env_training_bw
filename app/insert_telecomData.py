from pyspark.sql import SparkSession
from utils.controller_logger import update_control_table 
from pyspark.sql.functions import col, regexp_extract, avg, count
import time
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("PostgreSQLETL")

def pyspark_pg_transform():
    start_time = time.time()
    spark = None
    row_count = 0 
    try:
        logger.info("Initializing Spark session")
        spark = SparkSession.builder \
            .appName("PostgreSQL CSV Load telecom data") \
            .config("spark.driver.extraClassPath", "/opt/spark/jars/postgresql-42.7.7.jar") \
            .config("spark.executor.extraClassPath", "/opt/spark/jars/postgresql-42.7.7.jar") \
            .getOrCreate()

        # Read CSV file
        logger.info("Reading CSV file telecom details")
        call_details = spark.read \
            .option("header", "true") \
            .option("inferSchema", "true") \
            .option("delimiter", ",") \
            .csv("/opt/kaggle/input/Telco_Churn_Details2.csv")
        row_count = call_details.count()
        logger.info(f"Read {row_count} rows from CSV")
        # Show schema for verification
        call_details.printSchema()
        
        # Write to PostgreSQL
        logger.info("Writing data to PostgreSQL")
        call_details.write \
            .format("jdbc") \
            .option("url", "jdbc:postgresql://db-demo/mydb") \
            .option("dbtable", "dev.churn_details") \
            .option("user", "admin") \
            .option("password", "admin") \
            .mode("append") \
            .save()
        
        end_time = time.time()
        execution_time = end_time - start_time
        logger.info(f"PySpark job completed successfully in {execution_time:.2f} seconds")
        
       #  Log success to control table
        update_control_table(spark, status=True, rows_processed=row_count)

    except Exception as e:
        logger.error(f"Job failed with error: {str(e)}")

        if spark:
            # Log failure to control table
            update_control_table(spark, status=False, rows_processed=0, error_message=str(e))

        raise  # Reraise the exception if needed
    finally:
        if spark:
            spark.stop()
            logger.info("Spark session closed")

# Execute the function
if __name__ == "__main__":
    pyspark_pg_transform()
