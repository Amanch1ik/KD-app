#!/bin/sh
set -e

# Migrations
echo "Applying database migrations"
python manage.py migrate --noinput

# Collect static
echo "Collecting static files"
python manage.py collectstatic --noinput --clear

# Start ASGI server (Gunicorn + Uvicorn worker)
echo "Starting ASGI server"
exec gunicorn \
  --bind 0.0.0.0:8000 \
  --workers 3 \
  --timeout 120 \
  -k uvicorn.workers.UvicornWorker \
  karakoldelivery.asgi:application
