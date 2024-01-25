# django_celery/celery.py

import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "cortex.settings")
app = Celery("django_celery")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.conf.event_serializer = 'pickle' # this event_serializer is optional. somehow i missed this when writing this solution and it still worked without.
app.conf.task_serializer = 'pickle'
app.conf.result_serializer = 'pickle'
app.conf.accept_content = ['application/json', 'application/x-python-serialize']
app.conf.task_accept_content = ['application/json', 'application/x-python-serialize']
app.conf.result_accept_content = ['application/json', 'application/x-python-serialize']

# important note : by default celery autodiscover_tasks() will look for tasks.py in each app folder
# since our tasks are in voice/processing/tasks.py we need to specify the path to it
# check CELERY_IMPORTS in django_celery/settings.py
# https://docs.celeryq.dev/en/latest/userguide/configuration.html#std-setting-imports
# another way is to pass package names to autodiscover_tasks()
# https://docs.celeryq.dev/en/latest/django/first-steps-with-django.html  look for: CELERY_IMPORTS

app.autodiscover_tasks()
