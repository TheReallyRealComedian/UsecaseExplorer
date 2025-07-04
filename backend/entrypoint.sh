#!/bin/sh

# Exit immediately if a command exits with a non-zero status.
set -e

# Wait for the database to be ready
echo "Waiting for postgres..."
while ! nc -z db 5432; do
  sleep 0.1
done
echo "PostgreSQL started"

# Run database migrations
echo "Running database migrations..."
flask db upgrade

# Execute the command passed to this script (the gunicorn command)
exec "$@"