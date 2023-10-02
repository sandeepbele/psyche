#!/bin/bash



# Run migrations
python manage.py migrate

# Collect static files
python manage.py collectstatic --noinput

# Start Gunicorn
exec gunicorn -b 0.0.0.0:8000 enigma.wsgi:application
