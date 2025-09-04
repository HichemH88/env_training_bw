# transform_duckdb_with_condition.py
import duckdb
import psycopg2
import os
import yaml  
from typing import Dict, List, Any

DB_FILE = "/app/my_data.duckdb"
CONFIG_FILE = "/app/transform_rules.yaml"

# PostgreSQL connection parameters (update these with your actual credentials)
POSTGRES_CONFIG = {
    "host": "db-demo",
    "port": "5432",
    "database": "mydb",
    "user": "admin",
    "password": "admin",
    "options":"-c search_path=gold"
}

def load_config(config_file=CONFIG_FILE):
    """Load YAML config file"""
    with open(config_file, "r") as f:
        return yaml.safe_load(f)

def check_existing_database():
    if not os.path.exists(DB_FILE):
        print(f"❌ Database file not found: {DB_FILE}")
        return None
    return duckdb.connect(DB_FILE)

def get_postgres_connection():
    """Create and return PostgreSQL connection"""
    try:
        conn = psycopg2.connect(**POSTGRES_CONFIG)
        print("✅ Connected to PostgreSQL successfully")
        return conn
    except Exception as e:
        print(f"❌ Error connecting to PostgreSQL: {e}")
        return None

def get_column_names(con, table_name):
    """Get actual column names from the table using PRAGMA table_info"""
    try:
        cols = con.execute(f"PRAGMA table_info({table_name})").fetchall()
        return [col[1] for col in cols]
    except Exception as e:
        print(f"❌ Error getting column names for {table_name}: {e}")
        try:
            result = con.execute(f"SELECT * FROM {table_name} LIMIT 0")
            return [desc[0] for desc in result.description]
        except:
            return []

def build_where_clause(conditions):
    """Convert list of conditions to proper SQL WHERE clause"""
    if not conditions:
        return ""
    
    if isinstance(conditions, list):
        return " AND ".join([f"({cond})" for cond in conditions])
    elif isinstance(conditions, str):
        return conditions
    else:
        raise ValueError(f"Invalid conditions format: {conditions}")

def get_duckdb_table_schema(con, table_name: str) -> List[Dict]:
    """Get schema information from DuckDB table"""
    schema_query = f"""
    SELECT column_name, data_type 
    FROM information_schema.columns 
    WHERE table_name = '{table_name}'
    """
    try:
        result = con.execute(schema_query).fetchall()
        return [{"column_name": row[0], "data_type": row[1]} for row in result]
    except Exception as e:
        print(f"❌ Error getting schema for {table_name}: {e}")
        return []

def create_postgres_table(pg_conn, table_name: str, schema: List[Dict]):
    """Create PostgreSQL table based on DuckDB schema"""
    try:
        with pg_conn.cursor() as cursor:
            # Generate column definitions
            column_defs = []
            for col in schema:
                duckdb_type = col["data_type"]
                # Map DuckDB types to PostgreSQL types
                pg_type = map_duckdb_to_postgres_type(duckdb_type)
                column_defs.append(f'"{col["column_name"]}" {pg_type}')
            
            create_table_sql = f"""
            CREATE TABLE IF NOT EXISTS {table_name} (
                {', '.join(column_defs)}
            )
            """
            
            cursor.execute(create_table_sql)
            pg_conn.commit()
            print(f"✅ Created PostgreSQL table: {table_name}")
            
    except Exception as e:
        print(f"❌ Error creating PostgreSQL table {table_name}: {e}")
        pg_conn.rollback()

def map_duckdb_to_postgres_type(duckdb_type: str) -> str:
    """Map DuckDB data types to PostgreSQL data types"""
    type_mapping = {
        "BIGINT": "BIGINT",
        "INTEGER": "INTEGER",
        "SMALLINT": "SMALLINT",
        "TINYINT": "SMALLINT",
        "DOUBLE": "DOUBLE PRECISION",
        "FLOAT": "REAL",
        "REAL": "REAL",
        "VARCHAR": "VARCHAR",
        "CHAR": "CHAR",
        "TEXT": "TEXT",
        "BOOLEAN": "BOOLEAN",
        "DATE": "DATE",
        "TIMESTAMP": "TIMESTAMP",
        "TIME": "TIME",
        "DECIMAL": "DECIMAL",
        "NUMERIC": "NUMERIC"
    }
    
    # Handle types with parameters (e.g., VARCHAR(255))
    if "(" in duckdb_type:
        base_type = duckdb_type.split("(")[0].upper()
        if base_type in type_mapping:
            return duckdb_type.replace(base_type, type_mapping[base_type])
    
    return type_mapping.get(duckdb_type.upper(), "TEXT")

def load_to_postgres(duckdb_conn, pg_conn, table_name: str, pg_table_name: str = None):
    """Load data from DuckDB to PostgreSQL"""
    pg_table_name = pg_table_name or table_name
    
    try:
        # Get schema from DuckDB
        schema = get_duckdb_table_schema(duckdb_conn, table_name)
        if not schema:
            print(f"❌ Could not get schema for table {table_name}")
            return False
        
        # Create PostgreSQL table
        create_postgres_table(pg_conn, pg_table_name, schema)
        
        # Load data in batches
        with duckdb_conn.cursor() as duck_cursor:
            with pg_conn.cursor() as pg_cursor:
                # Get column names for INSERT statement
                columns = [col["column_name"] for col in schema]
                placeholders = ", ".join(["%s"] * len(columns))
                insert_sql = f'INSERT INTO {pg_table_name} ({", ".join(columns)}) VALUES ({placeholders})'
                
                # Read data in batches
                batch_size = 1000
                offset = 0
                total_rows = 0
                
                while True:
                    query = f"SELECT * FROM {table_name} LIMIT {batch_size} OFFSET {offset}"
                    batch_data = duck_cursor.execute(query).fetchall()
                    
                    if not batch_data:
                        break
                    
                    # Insert batch into PostgreSQL
                    pg_cursor.executemany(insert_sql, batch_data)
                    total_rows += len(batch_data)
                    offset += batch_size
                
                pg_conn.commit()
                print(f"✅ Loaded {total_rows} rows from {table_name} to PostgreSQL table {pg_table_name}")
                return True
                
    except Exception as e:
        print(f"❌ Error loading {table_name} to PostgreSQL: {e}")
        pg_conn.rollback()
        return False

def transform_table(con, table_name, rename_map=None, drop_cols=None, rules=None, conditions=None, new_table=None, load_to_pg: bool = False, pg_conn=None):
    """Transform a table and optionally load to PostgreSQL"""
    rename_map = rename_map or {}
    drop_cols = drop_cols or []
    rules = rules or {}
    conditions = conditions or []
    new_table = new_table or table_name

    cols = get_column_names(con, table_name)
    
    select_parts = []
    for col in cols:
        if col in drop_cols:
            continue
        elif col in rename_map:
            select_parts.append(f'"{col}" AS "{rename_map[col]}"')
        else:
            select_parts.append(f'"{col}"')

    for new_col, expr in rules.items():
        select_parts.append(f"({expr}) AS \"{new_col}\"")

    select_sql = ", ".join(select_parts)

    query = f"""
    CREATE OR REPLACE TABLE {new_table} AS
    SELECT {select_sql}
    FROM "{table_name}"
    """

    where_clause = build_where_clause(conditions)
    if where_clause:
        query += f" WHERE {where_clause}"

    print(f"🚀 Executing transformation query:\n{query}")
    
    try:
        con.execute(query)
        print(f"✅ Transformed {table_name} → {new_table}")
        
        # Load to PostgreSQL if requested
        if load_to_pg and pg_conn:
            load_to_postgres(con, pg_conn, new_table, new_table)
        
        # Show result structure
        result_cols = get_column_names(con, new_table)
        print(f"📋 Result columns: {result_cols}")
        
    except Exception as e:
        print(f"❌ Error transforming {table_name}: {e}")
        raise

if __name__ == "__main__":
    config = load_config()
    
    if "tables" not in config:
        raise ValueError("Config file must contain 'tables' key")
    
    # Connect to both databases
    duckdb_conn = check_existing_database()
    if duckdb_conn is None:
        exit(1)
    
    pg_conn = get_postgres_connection()
    if pg_conn is None:
        print("⚠️  PostgreSQL connection failed, continuing without PostgreSQL loading")
        pg_conn = None

    # Get PostgreSQL loading configuration
    load_to_postgres_flag = config.get("load_to_postgres", False)
    postgres_tables = config.get("postgres_tables", {})

    for table_name, table_config in config["tables"].items():
        print(f"\n🚀 Processing: {table_name}")
        
        # Check if this table should be loaded to PostgreSQL
        should_load_to_pg = load_to_postgres_flag or table_config.get("load_to_postgres", False)
        pg_table_name = postgres_tables.get(table_name, table_name)
        
        # Regular table transformation
        transform_table(
            duckdb_conn, 
            table_name, 
            rename_map=table_config.get("rename_map", {}),
            drop_cols=table_config.get("drop_cols", []),
            rules=table_config.get("rules", {}),
            conditions=table_config.get("conditions", []),
            new_table=table_config.get("new_table"),
            load_to_pg=should_load_to_pg,
            pg_conn=pg_conn
        )

    # Close connections
    duckdb_conn.close()
    if pg_conn:
        pg_conn.close()
    
    print("\n✅ All transformations completed!")