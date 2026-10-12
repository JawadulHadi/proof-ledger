#!/usr/bin/env sh
# Vercel build step. Vercel installs requirements.txt first, then runs this (vercel.json
# buildCommand). Vercel has no start command or pre-deploy hook, so the one-off steps that
# start.sh runs on Render happen here instead. Called through `sh`, so file mode doesn't matter.
set -e

# Hashed static files for WhiteNoise; staticfiles/ ships inside the function bundle.
python manage.py collectstatic --noinput

# Only production builds touch the database. Preview builds (every pull request) must never
# migrate or seed the live schema. All three commands are idempotent.
if [ "$VERCEL_ENV" = "production" ]; then
  python manage.py migrate --noinput
  python manage.py seed_demo
  # Creates the admin user once from DJANGO_SUPERUSER_USERNAME / _EMAIL / _PASSWORD.
  if [ -n "$DJANGO_SUPERUSER_USERNAME" ]; then
    python manage.py createsuperuser --noinput || true
  fi
fi
