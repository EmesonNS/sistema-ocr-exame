#!/bin/sh
set -e

if [ "${RUN_MIGRATIONS_ON_STARTUP:-false}" = "true" ]; then
  echo "Running database migrations..."
  alembic upgrade head
else
  echo "Skipping database migrations on startup."
fi

echo "Starting process: $*"
exec "$@"
