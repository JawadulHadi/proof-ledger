#!/usr/bin/env sh
# Render build step: install, collect static files.
set -e
pip install -r requirements.txt
python manage.py collectstatic --noinput
