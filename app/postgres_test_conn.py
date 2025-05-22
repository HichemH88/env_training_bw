# wait-for-postgres.py
import time
import psycopg2
from psycopg2 import OperationalError

while True:
    try:
        conn = psycopg2.connect("postgres://admin:admin@db-demo:5432/mydb")
        conn.close()
        print("Postgres is ready.")
        break
    except OperationalError as e:
        print("Waiting for Postgres...", e)
        time.sleep(2)
