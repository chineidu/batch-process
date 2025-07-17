import asyncio
import os
import time
import traceback
import warnings
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator

import httpx
import torch
from fastapi import FastAPI, HTTPException, Request, status

from src.api.utilities import create_logger
from src.config import app_config
from src.utilities.model_utils import load_gliner_model

warnings.filterwarnings("ignore")
logger = create_logger(name="app_utils")

MAX_WORKERS: int = os.cpu_count() - 1  # type: ignore

DUMMY_DATA: dict[str, Any] = {
    "data": [
        {
            "id": "1",
            "text": "treehouse cart payment communion retail store with levy through merrybet",
        },
        {"id": "2", "text": "alat transfer opay get drugs"},
    ]
}


class ModelManager:
    """A singleton class that manages the ML model, its dependencies, and prediction cache.

    This class ensures only one instance of the model is loaded in memory and provides
    methods to access and manage the model, dependencies, and cache.
    """

    _instance: "ModelManager | None" = None
    _model: nn.Module | None = None
    _is_initialized: bool = False

    def __new__(cls) -> "ModelManager":
        """Create or return the singleton instance of ModelManager.

        Returns
        -------
        ModelManager
            The singleton instance of ModelManager
        """
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_model()  # noqa: SLF001
            cls._instance._is_initialized = True  # noqa: SLF001
        return cls._instance

    def _load_model(self) -> None:
        """Load the ML model, dependencies, and initialize the prediction cache.

        Raises
        ------
        HTTPException
            If there is an error loading the model or dependencies
        """
        try:
            self._model = load_gliner_model(app_config.model.model_path)
            logger.info("Model successfully loaded...")

        except Exception as e:
            logger.error(f"Error loading model: {e} \nTraceback: {traceback.format_exc()}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error loading model and dependencies",
            ) from e

    def __init__(self) -> None:
        if not self._is_initialized:
            self._load_model()

    def get_components(self) -> dict[str, Any]:
        """Get the components of the model manager."""
        return {"model": self._model}

    def clear_cache(self) -> None:
        """Clear and reload the model."""
        self._model = None


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
        model_manager: ModelManager = ModelManager()
        app.state.model_manager = model_manager

        # Log device information
        if torch.cuda.is_available():
            logger.info(f"GPU Device Name: {torch.cuda.get_device_name(0)}")
            logger.info(
                f"GPU Memory: {torch.cuda.get_device_properties(0).total_memory / (1024**3):.2f} GB"
            )
        else:
            logger.warning("GPU is NOT available!")

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
    url: str = f"http://127.0.0.1:{app_config.api.server.port}{app_config.api.prefix}/predict"
    try:
        async with httpx.AsyncClient() as client:
            response: httpx.Response = await client.post(url, json=DUMMY_DATA, timeout=30.0)
            if response.status_code == 200 or response.status_code == 202:
                logger.info("HTTP warmup request successful")
            else:
                logger.warning(f"HTTP warmup request failed with status: {response.status_code}")
    except Exception as e:
        logger.error(f"Error during HTTP warmup request: {e} \nTraceback: {traceback.format_exc()}")
