#!/bin/sh
set -e  # при ошибке контейнер сразу завершится

echo "Running migrations..."
python manage.py migrate --noinput

echo "Collecting static files..."
python manage.py collectstatic --noinput

echo "Starting application..."
exec "$@"
