#!/bin/sh
set -e

echo "Waiting for Postgres at ${POSTGRES_HOST:-db}:${POSTGRES_PORT:-5432}..."
until pg_isready -h "${POSTGRES_HOST:-db}" -p "${POSTGRES_PORT:-5432}" -U "${POSTGRES_USER:-meraki}" > /dev/null 2>&1; do
  sleep 1
done
echo "Postgres is ready."

python manage.py migrate --noinput
python manage.py collectstatic --noinput

exec "$@"
