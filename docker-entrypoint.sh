#!/bin/bash
set -e

# ── Wait for Postgres ─────────────────────────────────────────────────────────
# Triggered if DATABASE_URL points to a service named 'db', or WAIT_FOR_DB=true
if [[ "$DATABASE_URL" == *"@db:"* ]] || [[ "$WAIT_FOR_DB" == "true" ]]; then
  echo "⏳ Waiting for PostgreSQL..."
  MAX_TRIES=30
  TRIES=0
  while ! nc -z db 5432; do
    sleep 1
    TRIES=$((TRIES + 1))
    if [ "$TRIES" -ge "$MAX_TRIES" ]; then
      echo "❌ PostgreSQL did not become ready in time. Aborting."
      exit 1
    fi
  done
  echo "✅ PostgreSQL is up."
fi

# ── Run Alembic migrations ────────────────────────────────────────────────────
# Always run on startup. Alembic is idempotent — it's safe to run on every boot.
# On Railway/Docker, this applies any pending schema changes before the app starts.
echo "🔄 Running database migrations..."
alembic upgrade head
echo "✅ Migrations complete."

# ── Start the application ─────────────────────────────────────────────────────
exec "$@"
