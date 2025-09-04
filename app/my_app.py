from fastapi import FastAPI
from /app/get_data_parquet_minio import main

app = FastAPI()

@app.post("/run-script")
def run_script():
    result = main()
    return {"status": "success", "result": result}