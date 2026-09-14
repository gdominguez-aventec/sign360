#!/bin/sh
set -e

if [ -n "$DATABASE_HOST" ]; then
  echo "Esperant la base de dades a $DATABASE_HOST:${DATABASE_PORT:-5432}..."
  until pg_isready -h "$DATABASE_HOST" -p "${DATABASE_PORT:-5432}" >/dev/null 2>&1; do
    sleep 1
  done
fi

python manage.py migrate --noinput
python manage.py collectstatic --noinput

exec "$@"
