#!/bin/sh
set -e

# Ensure persistent directories exist
mkdir -p /app/data /app/uploads

# Run safe, non-destructive database initialization and seeding
echo "[Entrypoint] Initializing database tables and verifying seed data..."
python seed.py

# Start backend server bound to 0.0.0.0
echo "[Entrypoint] Starting Uvicorn server on 0.0.0.0:8000..."
exec uvicorn main:app --host 0.0.0.0 --port 8000

