#!/usr/bin/env bash

python manage.py migrate --noinput
python manage.py collectstatic --noinput
python manage.py create_admin

gunicorn pos_project.wsgi:application