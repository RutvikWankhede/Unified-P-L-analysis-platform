FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY unified-pl-system/backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /app/requirements.txt

# Copy backend source code and seed data
COPY unified-pl-system/backend /app
COPY data/default/unified_pnl_enterprise_demo.csv /app/data/default/unified_pnl_enterprise_demo.csv
COPY unified_pnl_enterprise_demo.csv /app/demo_dataset.csv
COPY unified_pnl_enterprise_demo.csv /app/unified_pnl_enterprise_demo.csv

# Ensure persistent directories exist
RUN mkdir -p /app/data /app/uploads

# Ensure entrypoint script is executable
RUN chmod +x /app/entrypoint.sh 2>/dev/null || true

# Expose backend port
EXPOSE 8000

# Healthcheck using curl
HEALTHCHECK --interval=10s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/system/health || curl -f http://localhost:8000/health || exit 1

# Start container via entrypoint
ENTRYPOINT ["/bin/sh", "/app/entrypoint.sh"]
