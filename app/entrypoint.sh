#!/bin/bash
set -e

echo "Waiting for PostgreSQL to be ready..."

# Wait until PostgreSQL is ready
until pg_isready -h db -p 5432 -U myuser > /dev/null 2>&1; do
  sleep 1
done

echo "PostgreSQL is ready. Starting Python app..."

exec "$@"
