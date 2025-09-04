FROM python:3.11-slim

# Install system dependencies for DuckDB and general utilities
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libsqlite3-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Also install duckdb, pandas, fastapi, uvicorn
RUN pip install --no-cache-dir duckdb pandas

# Copy app code
COPY . .

# Make entrypoint executable
RUN chmod +x entrypoint.sh

# Run entrypoint script on container start
ENTRYPOINT ["./entrypoint.sh"]
