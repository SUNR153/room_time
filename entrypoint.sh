#!/bin/sh
# Ждём базу
echo "Waiting for PostgreSQL..."
while ! nc -z db 5432; do
  sleep 0.1
done
echo "PostgreSQL is ready"

# Собираем статические файлы (можно опционально)
mkdir -p /app/static
python manage.py collectstatic --noinput

# Запускаем Gunicorn
exec gunicorn roomtime.wsgi:application --bind 0.0.0.0:8000

