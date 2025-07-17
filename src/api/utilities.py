from __future__ import annotations

import asyncio
import os
import time
import traceback
import warnings
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncGenerator

import httpx
import joblib
from fastapi import FastAPI, HTTPException, Request, status

from src import PACKAGE_PATH, create_logger
from src.config import app_config

warnings.filterwarnings("ignore")
logger = create_logger(name="utilities")
MAX_WORKERS: int = os.cpu_count() - 1  # type: ignore
api_config = app_config.api_config
DUMMY_DATA: dict[str, Any] = {
    "data": [
        {
            "personId": "q0bPCRQH",
            "sex": "female",
            "age": 66.48,
            "pclass": 2,
            "sibsp": 0,
            "parch": 0,
            "fare": 149.22,
            "embarked": "q",
        }
    ]
}


class Modelmanager:
    """
    A singleton class that provides access to a machine learning model dictionary.

    This class ensures that the model dictionary is loaded only once and reused
    throughout the application's lifecycle.
    """

    _instance: Modelmanager | None = None
    _model_dict: dict[str, Any] | None = None
    _is_initialized: bool = False

    def __new__(cls) -> Modelmanager:
        """Create or return the singleton instance of Modelmanager."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_model_dict()  # noqa: SLF001

        return cls._instance

    def __init__(self) -> None:
        """Initialize the Modelmanager instance."""
        if not self._is_initialized:
            self._is_initialized = True

    def _load_model_dict(self) -> None:
        """Load the model dictionary from a file."""
        model_path: str = str(PACKAGE_PATH / Path(app_config.model.artifacts.model_path))
        with open(model_path, "rb") as f:
            self._model_dict = joblib.load(f)

    @property
    def model_dict(self) -> dict[str, Any]:
        """Return the model dictionary, loading it if necessary."""
        if self._model_dict is None:
            self._load_model_dict()
        return self._model_dict  # type: ignore

    def clear_cache(self) -> None:
        """Clear the model dictionary cache."""
        if self.model_dict is not None:
            self._model_dict = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Initialize and cleanup FastAPI application lifecycle.

    This context manager handles the initialization of model components during startup
    and cleanup during shutdown.
    """
    try:
        start_time: float = time.perf_counter()
        logger.info("Loading model during application startup...")

        # Init model and dependencies and store all components in app state
        model_manager: Modelmanager = Modelmanager()
        app.state.model_manager = model_manager

        # Wait a few seconds before making the first request
        await asyncio.sleep(1)
        # Warmup model to avoid latency during first request
        asyncio.create_task(perform_http_warmup())
        logger.info(f"Model initialized in {time.perf_counter() - start_time:.2f} seconds")

    except Exception as e:
        logger.error(f"Failed to initialize model during startup: {e}")
        raise

    try:
        yield
    finally:
        # Cleanup
        if hasattr(app.state, "model_manager"):
            try:
                app.state.model_manager.clear_cache()
            except Exception as e:
                logger.error(f"Error during cache cleanup: {e}")


def get_model_manager(request: Request) -> dict[str, Any]:
    """Get the model components from the app state.

    Parameters
    ----------
    request : Request
        The FastAPI request object containing application state.

    Returns
    -------
    dict[str, Any]
        Dictionary containing model components and their configurations.

    Raises
    ------
    HTTPException
        If model manager is not loaded or initialized in the application state.
    """
    if not hasattr(request.app.state, "model_manager") or request.app.state.model_manager is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Model manager not loaded. Please try again later.",
        )
    return request.app.state.model_manager.get_components()


async def perform_http_warmup() -> None:
    """
    Perform HTTP warmup request after the server has started.

    This function sends a POST request to the prediction endpoint with dummy data
    to prevent cold start delays.
    """
    # Wait for server to be fully initialized
    await asyncio.sleep(1)

    logger.info("Performing HTTP warmup request...")
    print(f"Port: {app_config.api_config.server.port}")
    url: str = f"http://127.0.0.1:{api_config.server.port}{api_config.prefix}/predict-single"
    try:
        async with httpx.AsyncClient() as client:
            response: httpx.Response = await client.post(url, json=DUMMY_DATA, timeout=30.0)
            if response.status_code == 200 or response.status_code == 202:
                logger.info("HTTP warmup request successful")
            else:
                logger.warning(f"HTTP warmup request failed with status: {response.status_code}")
    except Exception as e:
        logger.error(f"Error during HTTP warmup request: {e} \nTraceback: {traceback.format_exc()}")
