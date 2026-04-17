#!/usr/bin/env bash

python manage.py migrate --noinput
python manage.py collectstatic --noinput
gunicorn pos_project.wsgi:application --bind 0.0.0.0:$PORT