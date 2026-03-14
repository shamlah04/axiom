#!/bin/bash
set -e

if [[ "$DATABASE_URL" == *"@db:"* ]] || [[ "$WAIT_FOR_DB" == "true" ]]; then
  echo "⏳ Waiting for PostgreSQL..."
  while ! nc -z db 5432; do sleep 1; done
  echo "✅ PostgreSQL is up."
fi

echo "🔄 Running database migrations..."
alembic upgrade head
echo "✅ Migrations complete."

exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}" --proxy-headers --forwarded-allow-ips="*"
