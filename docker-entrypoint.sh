#!/bin/bash
set -e

echo "🟢 Entrypoint starting..."

# Extract host and port from DATABASE_URL
if [[ "$DATABASE_URL" =~ @([^/:]+)(:([0-9]+))? ]]; then
  DB_HOST="${BASH_REMATCH[1]}"
  DB_PORT="${BASH_REMATCH[3]:-5432}"
  
  if [[ "$WAIT_FOR_DB" == "true" ]]; then
    echo "⏳ Waiting for database at $DB_HOST:$DB_PORT..."
    while ! nc -z "$DB_HOST" "$DB_PORT"; do
      sleep 1
    done
    echo "✅ Database is up."
  fi
fi

echo "🔄 Running database migrations..."
alembic upgrade head
echo "✅ Migrations complete."

echo "🚀 Starting Uvicorn in background..."
uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8080}" --log-level info &
UVICORN_PID=$!

sleep 5

echo "🔍 Testing internal connectivity..."
if curl -s http://localhost:"${PORT:-8080}"/health; then
    echo "✅ Internal health check SUCCEEDED"
else
    echo "❌ Internal health check FAILED"
    # Try 0.0.0.0
    if curl -s http://0.0.0.0:"${PORT:-8080}"/health; then
        echo "✅ Internal 0.0.0.0 health check SUCCEEDED"
    else
        echo "❌ Internal 0.0.0.0 health check FAILED"
    fi
fi

echo "📋 Active ports:"
netstat -tulpn || ss -tulpn || echo "netstat/ss not found"

# Bring uvicorn to foreground
wait $UVICORN_PID
