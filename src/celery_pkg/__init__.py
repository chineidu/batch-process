from __future__ import annotations

from pathlib import Path
from typing import Any

import joblib
from celery import Task

from src import PACKAGE_PATH
from src.config import app_config

from .app import celery_app

__all__ = ["celery_app", "BaseCustomTask"]


class BaseCustomTask(Task):
    """
    A custom base task class for Celery tasks with automatic retry configuration.

    Attributes
    ----------
    autoretry_for : tuple
        A tuple of exception types for which the task should automatically retry.
    throws : tuple
        A tuple of exception types for which full traceback should be logged on retry.
    default_retry_delay : int
        The default delay between retries in seconds.
    max_retries : int
        The maximum number of retries allowed for the task.
    retry_backoff : bool
        Enables exponential backoff for retry delays.
    retry_backoff_max : int
        The maximum delay in seconds for exponential backoff.
    """
    autoretry_for = (Exception,)
    throws = (Exception,)  # Log full traceback on retry
    default_retry_delay = 30  # 30 seconds
    max_retries = 5
    retry_backoff = True  # exponential backoff
    retry_backoff_max = 300  # 10 minutes

