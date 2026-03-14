#!/bin/bash
set -e

# Extract host and port from DATABASE_URL
# Format: postgresql+asyncpg://user:pass@host:port/dbname
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

echo "🚀 Starting on port ${PORT:-8000}"
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
