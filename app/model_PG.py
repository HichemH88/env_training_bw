import pickle
import psycopg2

# Train model
from sklearn.linear_model import LogisticRegression
model = LogisticRegression()
model.fit([[0, 1], [1, 0]], [0, 1])

# Serialize
model_blob = pickle.dumps(model)

# Save to DB
conn = psycopg2.connect(
    dbname="mydb", user="admin", password="admin", host="db-demo", port=5432
)
cur = conn.cursor()
cur.execute("CREATE TABLE IF NOT EXISTS dev.model_store (id SERIAL PRIMARY KEY, model BYTEA);")
cur.execute("INSERT INTO dev.model_store (model) VALUES (%s);", (psycopg2.Binary(model_blob),))
conn.commit()
cur.close()
conn.close()
