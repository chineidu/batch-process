from __future__ import annotations

from pathlib import Path
from typing import Any

import joblib

from celery import Task
from config import app_config
from src import PACKAGE_PATH

from .app import celery_app

__all__ = ["celery_app", "BaseCustomTask", "BaseMLTask"]


class BaseCustomTask(Task):
    autoretry_for = (Exception,)
    throws = (Exception,)  # Log full traceback on retry
    default_retry_delay = 30  # 30 seconds
    max_retries = 5
    retry_backoff = True  # exponential backoff
    retry_backoff_max = 300  # 10 minutes


class BaseMLTask:
    _instance: BaseMLTask | None = None
    _model_dict: dict[str, Any] | None = None
    _is_initialized: bool = False

    def __new__(cls) -> BaseMLTask:
        """Create or return the singleton instance of BaseMLTask."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_model_dict()  # noqa: SLF001

        return cls._instance
    
    def __init__(self) -> None:
        if not self._is_initialized:
            self._is_initialized = True

    def _load_model_dict(self) -> None:
        """Load the model dictionary from a file."""
        model_path: str = str(PACKAGE_PATH / Path(app_config.model.artifacts.model_path))
        with open(model_path, "rb") as f:
            self._model_dict = joblib.load(f)

    @property
    def model_dict(self) -> dict[str, Any]:
        """Return the model dictionary."""
        if self._model_dict is None:
            self._load_model_dict()
        return self._model_dict  # type: ignore
