FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for PostgreSQL and compiling
RUN apt-get update && apt-get install -y libpq-dev gcc

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Run alembic migrations and start server
CMD alembic upgrade head && uvicorn main:app --host 0.0.0.0 --port 10000
