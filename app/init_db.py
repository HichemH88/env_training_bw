import psycopg2
import time

# Retry logic
MAX_RETRIES = 10
retries = 0

while retries < MAX_RETRIES:
    try:
        conn = psycopg2.connect(
            dbname="mydb",
            user="admin",
            password="admin",
            host="db-demo",
            port="5432"
            
        )
        conn.autocommit = True
        break
    except psycopg2.OperationalError as e:
        print(f"❌ DB not ready: {e}")
        retries += 1
        time.sleep(3)
else:
    print("❌ Could not connect after multiple attempts.")
    exit(1)

# Create table and insert data
with conn.cursor() as cur:
    cur.execute("""
        CREATE TABLE IF NOT EXISTS dev.orders (
            id SERIAL PRIMARY KEY,
            customer_name VARCHAR(100),
            product_name VARCHAR(100),
            quantity INT,
            order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    cur.execute("""
        INSERT INTO dev.orders (customer_name, product_name, quantity)
        VALUES 
            ('Alice', 'Laptop', 1),
            ('Bob', 'Smartphone', 2),
            ('Carol', 'Headphones', 3)
        ON CONFLICT DO NOTHING;
    """)

print("✅ Table 'orders' created and data inserted.")
conn.close()
