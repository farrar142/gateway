from __future__ import absolute_import
import os
import time
import dotenv
from django.apps import apps
from celery import Celery, shared_task

dotenv.load_dotenv()
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "base.settings.prod")
app = Celery(os.getenv("CELERY_APP", "base"))
app.config_from_object("django.conf:settings", namespace="CELERY")
app.conf.worker_max_tasks_per_child = 100
# app.autodiscover_tasks(lambda: [n.name for n in apps.get_app_configs()], force=True)
app.autodiscover_tasks()
