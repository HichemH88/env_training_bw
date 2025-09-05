import yaml
import psycopg2

# PostgreSQL connection parameters
POSTGRES_CONFIG = {
    "host": "db-demo",
    "port": "5432",
    "database": "mydb",
    "user": "admin",
    "password": "admin",
    "options": "-c search_path=gold"
}


def execute_postgres_sql(sql, config=POSTGRES_CONFIG):
    """Execute a SQL statement in Postgres"""
    conn = psycopg2.connect(
        host=config["host"],
        port=config["port"],
        database=config["database"],
        user=config["user"],
        password=config["password"],
        options=config.get("options")
    )
    cur = conn.cursor()
    cur.execute(sql)
    conn.commit()
    cur.close()
    conn.close()


def load_config(config_file):
    """Load YAML config file"""
    with open(config_file, "r") as f:
        return yaml.safe_load(f)

def transform_table_postgres(cfg, table_name):
    """Generate and execute Postgres SQL for table/view based on YAML config"""
    output_cols = cfg.get("output_cols", [])
    rename_map = cfg.get("rename_map", {})
    rules = cfg.get("rules", {})
    condition = cfg.get("condition")
    aggregations = cfg.get("aggregations", {})
    group_by = cfg.get("group_by", [])
    new_object = cfg.get("new_object", table_name)
    object_type = cfg.get("object_type", "table")
    source_table = cfg.get("source_table", table_name)

    select_parts = []

    # Keep original output columns
    for col in output_cols:
        select_parts.append(rename_map.get(col, col))

    # Add rules
    for new_col, expr in rules.items():
        select_parts.append(f"{expr} AS {new_col}")

    # Add aggregations (but don't remove existing columns)
    for new_col, expr in aggregations.items():
        select_parts.append(f"{expr} AS {new_col}")

    select_sql = ", ".join(select_parts)

    query = f"SELECT {select_sql} FROM {source_table}"
    if condition:
        query += f" WHERE {condition}"
    if group_by:
        query += f" GROUP BY {', '.join(group_by)}"

    if object_type == "view":
        ddl = f"CREATE OR REPLACE VIEW {new_object} AS {query}"
    else:
        ddl = f"CREATE TABLE IF NOT EXISTS {new_object} AS {query}"

    execute_postgres_sql(ddl)
    print(f"✅ Created {object_type.upper()} {new_object} from {source_table}")



if __name__ == "__main__":
    CONFIG_FILE = "agg_rules.yaml"
    config = load_config(CONFIG_FILE)

    for table_name, cfg in config.get("tables", {}).items():
        print(f"\n🚀 Processing table/view: {table_name}")
        transform_table_postgres(cfg, table_name)

    print("\n✅ All transformations completed!")
