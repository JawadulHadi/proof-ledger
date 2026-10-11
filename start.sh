#!/usr/bin/env sh
# Free hosts have no pre-deploy hook, so migrate and seed on boot (both are idempotent).
set -e
python manage.py migrate --noinput
python manage.py seed_demo
# Creates the admin user once from DJANGO_SUPERUSER_USERNAME / _EMAIL / _PASSWORD; ignored if it exists.
if [ -n "$DJANGO_SUPERUSER_USERNAME" ]; then
  python manage.py createsuperuser --noinput || true
fi
exec gunicorn config.wsgi:application --bind "0.0.0.0:${PORT:-8000}" --workers 2 --timeout 60
