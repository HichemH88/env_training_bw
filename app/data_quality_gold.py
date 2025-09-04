# data_profiling_gold.py
import psycopg2
import pandas as pd
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

def get_duplicate_query(table):
    """Build a duplicate detection SQL using all columns of a table"""
    with get_connection() as conn:
        cols = pd.read_sql(
            f"""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema='gold' AND table_name='{table}'
            ORDER BY ordinal_position;
            """,
            conn
        )["column_name"].tolist()

    if not cols:  # safety check
        return f"SELECT 0 AS duplicate_rows;"

    col_list = ", ".join([f'"{c}"' for c in cols])  # safely quote identifiers
    query = f"""
        SELECT COUNT(*) AS duplicate_rows
        FROM (
            SELECT {col_list}, COUNT(*) AS cnt
            FROM {table}
            GROUP BY {col_list}
            HAVING COUNT(*) > 1
        ) t;
    """
    return query

def summarize_table(table):
    """Run data profiling & quality checks for a table"""
    queries = {
        "row_count": f"SELECT COUNT(*) AS row_count FROM {table};",
        "col_info": f"""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_schema='gold' AND table_name='{table}';
        """,
        "null_counts": f"""
            SELECT 
                column_name,
                (xpath('/row/count/text()', xml_count))[1]::text::int AS null_count
            FROM (
                SELECT 
                    column_name,
                    query_to_xml(format(
                        'SELECT COUNT(*) FROM {table} WHERE %I IS NULL', column_name
                    ), false, true, '') AS xml_count
                FROM information_schema.columns
                WHERE table_schema='gold' AND table_name='{table}'
            ) t;
        """,
        "distinct_counts": f"""
            SELECT 
                column_name,
                (xpath('/row/count/text()', xml_count))[1]::text::int AS distinct_count
            FROM (
                SELECT 
                    column_name,
                    query_to_xml(format(
                        'SELECT COUNT(DISTINCT %I) FROM {table}', column_name
                    ), false, true, '') AS xml_count
                FROM information_schema.columns
                WHERE table_schema='gold' AND table_name='{table}'
            ) t;
        """
    }

    duplicate_query = get_duplicate_query(table)

    with get_connection() as conn:
        row_count = pd.read_sql(queries["row_count"], conn)
        col_info = pd.read_sql(queries["col_info"], conn)
        null_counts = pd.read_sql(queries["null_counts"], conn)
        distinct_counts = pd.read_sql(queries["distinct_counts"], conn)
        duplicates = pd.read_sql(duplicate_query, conn)

    # Merge results
    summary = col_info.merge(null_counts, on="column_name") \
                      .merge(distinct_counts, on="column_name")

    summary["row_count"] = row_count.iloc[0]["row_count"]
    summary["duplicate_rows"] = duplicates.iloc[0]["duplicate_rows"]

    return summary

def store_results(df, table_name):
    """Store profiling results into Postgres (gold.data_quality_report)"""
    create_sql = """
    CREATE TABLE IF NOT EXISTS gold.data_quality_report (
        table_name TEXT,
        column_name TEXT,
        data_type TEXT,
        row_count BIGINT,
        null_count BIGINT,
        distinct_count BIGINT,
        duplicate_rows BIGINT,
        report_date TIMESTAMP DEFAULT NOW()
    );
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(create_sql)

            rows = [
                (
                    table_name,
                    row["column_name"],
                    row["data_type"],
                    row["row_count"],
                    row["null_count"],
                    row["distinct_count"],
                    row["duplicate_rows"]
                )
                for _, row in df.iterrows()
            ]

            insert_sql = """
            INSERT INTO gold.data_quality_report
            (table_name, column_name, data_type, row_count, null_count, distinct_count, duplicate_rows)
            VALUES %s
            """
            execute_values(cur, insert_sql, rows)
        conn.commit()

def main():
    tables = get_tables()
    print(f"Found tables: {tables}")

    for table in tables:
        print(f"\n📊 Processing table: {table}")
        df_summary = summarize_table(table)
        store_results(df_summary, table)
        print(f"✅ Report stored for table {table}")

if __name__ == "__main__":
    main()
