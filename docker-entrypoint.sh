#!/bin/bash
set -e

# Wait for postgres to be ready
echo "Waiting for postgres..."

while ! nc -z db 5432; do
  sleep 0.1
done

echo "PostgreSQL started"

# Run migrations
echo "Running alembic migrations..."
alembic upgrade head

# Execute the CMD
exec "$@"
