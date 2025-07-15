from celery import Task

from .app import celery_app

__all__ = ["celery_app"]


class EmailTask(Task):
    autoretry_for = (Exception,)
    default_retry_delay = 30  # 30 seconds
    max_retries = 3
    retry_backoff = True  # exponential backoff
    retry_backoff_max = 600  # 10 minutes
    retry_jitter = True
