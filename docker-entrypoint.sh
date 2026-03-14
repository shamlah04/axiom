#!/bin/bash
set -e

# Run migrations
echo "🔄 Running migrations..."
alembic upgrade head

# Start app
echo "🚀 Starting uvicorn on port ${PORT:-8080}..."
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8080}" --log-level info --proxy-headers --forwarded-allow-ips="*"
