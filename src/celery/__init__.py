from celery import Task

from .app import celery_app

__all__ = ["celery_app"]


class EmailTask(Task):
    autoretry_for = (Exception,)
    throws = (Exception,)  # Log full traceback on retry
    default_retry_delay = 30  # 30 seconds
    max_retries = 5
    retry_backoff = True  # exponential backoff
    retry_backoff_max = 300  # 10 minutes
