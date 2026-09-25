#!/bin/bash

# Run migrations
python manage.py migrate

# Collect static files
python manage.py collectstatic --noinput

# Capture output of check for admin user
admin_exists=$(python manage.py shell -c "from django.contrib.auth.models import User; print(User.objects.filter(username='admin').exists())")

# Check if admin user exists
if [[ "$admin_exists" == "False" ]]; then
    # Create admin user
    python manage.py createsuperuser --noinput --username admin --email admin@example.com
    # Set admin password from environment variable
    python manage.py shell -c "from django.contrib.auth.models import User; user=User.objects.get(username='admin'); user.set_password('$ADMIN_PASSWORD'); user.save()"
fi

# Start Gunicorn
exec gunicorn -b 0.0.0.0:8000 enigma.wsgi:application
