#!/bin/bash
set -e

# Wait for postgres to be ready (Only if explicitly using 'db' host or specifically requested)
if [[ "$DATABASE_URL" == *"@db:"* ]] || [[ "$WAIT_FOR_DB" == "true" ]]; then
  echo "Waiting for postgres..."
  while ! nc -z db 5432; do
    sleep 0.1
  done
  echo "PostgreSQL started"
fi
# Skip migrations for now
# alembic upgrade head

# Execute the CMD
exec "$@"
