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
if alembic upgrade head; then
    echo "✅ Migrations complete."
else
    echo "❌ Migrations failed!"
    exit 1
fi

echo "🚀 Starting Uvicorn on port ${PORT:-8000}..."
echo "Current PATH: $PATH"
echo "Uvicorn path: $(which uvicorn || echo 'NOT FOUND')"

exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}" --log-level info --access-log
