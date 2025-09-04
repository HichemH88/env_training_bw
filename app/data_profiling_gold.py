# data_profiling_stats.py
import psycopg2
import pandas as pd
import math
import numpy as np
from psycopg2.extras import execute_values

POSTGRES_CONFIG = {
    "host": "db-demo",
    "port": "5432",
    "database": "mydb",
    "user": "admin",
    "password": "admin",
    "options": "-c search_path=gold"
}

def get_connection():
    return psycopg2.connect(**POSTGRES_CONFIG)

def get_tables():
    """List all tables in schema 'gold'"""
    query = """
    SELECT table_name 
    FROM information_schema.tables 
    WHERE table_schema = 'gold' AND table_type='BASE TABLE';
    """
    with get_connection() as conn:
        return pd.read_sql(query, conn)["table_name"].tolist()

def get_columns(table):
    """Get all columns and their data types"""
    query = f"""
    SELECT column_name, data_type
    FROM information_schema.columns
    WHERE table_schema='gold' AND table_name='{table}';
    """
    with get_connection() as conn:
        return pd.read_sql(query, conn)

def profile_numeric_column(table, column):
    """Return stats for numeric column (with percentiles)"""
    query = f"""
    SELECT
        MIN("{column}") AS min_val,
        MAX("{column}") AS max_val,
        AVG("{column}") AS avg_val,
        STDDEV("{column}") AS stddev_val,
        percentile_cont(0.25) WITHIN GROUP (ORDER BY "{column}") AS p25,
        percentile_cont(0.5)  WITHIN GROUP (ORDER BY "{column}") AS median,
        percentile_cont(0.75) WITHIN GROUP (ORDER BY "{column}") AS p75
    FROM {table};
    """
    with get_connection() as conn:
        return pd.read_sql(query, conn).iloc[0]

def profile_date_column(table, column):
    """Return stats for date/datetime column"""
    query = f"""
    SELECT
        MIN("{column}") AS min_date,
        MAX("{column}") AS max_date
    FROM {table};
    """
    with get_connection() as conn:
        return pd.read_sql(query, conn).iloc[0]

def clean_value(v):
    """Convert NaT/NaN to None for Postgres compatibility"""
    if v is None:
        return None
    if isinstance(v, float) and math.isnan(v):
        return None
    if v is pd.NaT or v is np.datetime64("NaT"):
        return None
    return v

def summarize_table(table):
    """Profile all numeric & date columns in a table"""
    cols = get_columns(table)
    results = []

    for _, row in cols.iterrows():
        col = row["column_name"]
        dtype = row["data_type"]

        if dtype in ["integer", "bigint", "smallint", "numeric", "real", "double precision", "decimal"]:
            stats = profile_numeric_column(table, col)
            results.append({
                "table_name": table,
                "column_name": col,
                "data_type": dtype,
                "min_val": clean_value(stats["min_val"]),
                "max_val": clean_value(stats["max_val"]),
                "avg_val": clean_value(stats["avg_val"]),
                "stddev_val": clean_value(stats["stddev_val"]),
                "p25": clean_value(stats["p25"]),
                "median": clean_value(stats["median"]),
                "p75": clean_value(stats["p75"]),
                "min_date": None,
                "max_date": None
            })

        elif dtype in ["date", "timestamp without time zone", "timestamp with time zone"]:
            stats = profile_date_column(table, col)
            results.append({
                "table_name": table,
                "column_name": col,
                "data_type": dtype,
                "min_val": None,
                "max_val": None,
                "avg_val": None,
                "stddev_val": None,
                "p25": None,
                "median": None,
                "p75": None,
                "min_date": clean_value(stats["min_date"]),
                "max_date": clean_value(stats["max_date"])
            })

    return pd.DataFrame(results)

def store_results(df):
    """Store profiling results into Postgres"""
    create_sql = """
    CREATE TABLE IF NOT EXISTS gold.data_profiling_stats (
        table_name TEXT,
        column_name TEXT,
        data_type TEXT,
        min_val NUMERIC,
        max_val NUMERIC,
        avg_val NUMERIC,
        stddev_val NUMERIC,
        p25 NUMERIC,
        median NUMERIC,
        p75 NUMERIC,
        min_date TIMESTAMP,
        max_date TIMESTAMP,
        report_date TIMESTAMP DEFAULT NOW()
    );
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(create_sql)

            rows = [
                (
                    row["table_name"],
                    row["column_name"],
                    row["data_type"],
                    clean_value(row["min_val"]),
                    clean_value(row["max_val"]),
                    clean_value(row["avg_val"]),
                    clean_value(row["stddev_val"]),
                    clean_value(row["p25"]),
                    clean_value(row["median"]),
                    clean_value(row["p75"]),
                    clean_value(row["min_date"]),
                    clean_value(row["max_date"])
                )
                for _, row in df.iterrows()
            ]

            insert_sql = """
            INSERT INTO gold.data_profiling_stats
            (table_name, column_name, data_type, min_val, max_val, avg_val, stddev_val,
             p25, median, p75, min_date, max_date)
            VALUES %s
            """
            execute_values(cur, insert_sql, rows)
        conn.commit()

def main():
    tables = get_tables()
    print(f"Found tables: {tables}")

    for table in tables:
        print(f"\n📊 Profiling table: {table}")
        df_stats = summarize_table(table)

        if not df_stats.empty:
            store_results(df_stats)
            print(f"✅ Stats stored for table {table}")
        else:
            print(f"⚠️ No numeric or date columns found in {table}")

if __name__ == "__main__":
    main()
