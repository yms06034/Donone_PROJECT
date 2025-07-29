#!/bin/sh

# Django 마이그레이션 실행
echo "Running Django migrations..."
python manage.py migrate

# Static 파일 수집
echo "Collecting static files..."
python manage.py collectstatic --noinput

# Gunicorn 실행
echo "Starting Gunicorn..."
exec "$@"