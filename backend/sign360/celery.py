import os

from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sign360.settings')

app = Celery('sign360')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
