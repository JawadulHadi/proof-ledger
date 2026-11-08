#!/usr/bin/env sh
# Render build step: install, build the React/TypeScript dashboard, collect static files.
set -e
pip install -r requirements.txt
# The built client is committed in core/static/app, so a host without Node still works.
if command -v npm >/dev/null 2>&1; then
  (cd frontend && npm ci --no-audit --no-fund && npm run build)
else
  echo "npm not found: using the committed core/static/app build"
fi
python manage.py collectstatic --noinput
