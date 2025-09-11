#!/bin/sh
set -e

# Wait for DB
if [ "$DATABASE" = "postgres" ]; then
  echo "Waiting for postgres..."
  while ! nc -z $DB_HOST $DB_PORT; do
    sleep 1
  done
fi

echo "Apply database migrations"
python manage.py migrate --noinput

echo "Collect static files"
python manage.py collectstatic --noinput --clear

echo "Starting server"
gunicorn karakoldelivery.wsgi:application --bind 0.0.0.0:8000 --workers 3

#!/bin/bash

# Выход при ошибке
set -e

# Ожидание запуска базы данных
if [ "$DATABASE" = "postgres" ]
then
    echo "Ожидание базы данных..."
    while ! nc -z $DB_HOST $DB_PORT; do
      sleep 0.1
    done
    echo "База данных запущена"
fi

# Выполнение миграций
python manage.py migrate --noinput

# Сбор статических файлов
python manage.py collectstatic --noinput

# Запуск Gunicorn
exec gunicorn \
    --bind 0.0.0.0:8000 \
    --workers 3 \
    --timeout 120 \
    karakoldelivery.wsgi:application
