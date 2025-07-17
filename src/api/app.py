import sys
import warnings

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes import health, prediction
from src.api.utilities import lifespan
from src.config import app_config

warnings.filterwarnings("ignore")

api_config = app_config.api_config


def create_application() -> FastAPI:
    """Create and configure a FastAPI application instance.

    This function initializes a FastAPI application with custom configuration settings,
    adds CORS middleware, and includes API route handlers.

    Returns
    -------
    FastAPI
        A configured FastAPI application instance.
    """
    app = FastAPI(
        title=api_config.title,
        description=api_config.description,
        version=api_config.version,
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=api_config.middleware.cors.allow_origins,
        allow_credentials=api_config.middleware.cors.allow_credentials,
        allow_methods=api_config.middleware.cors.allow_methods,
        allow_headers=api_config.middleware.cors.allow_headers,
    )

    # Include routers
    app.include_router(prediction.router, prefix=api_config.prefix)
    app.include_router(health.router, prefix=api_config.prefix)

    return app


app = create_application()

if __name__ == "__main__":
    try:
        uvicorn.run(
            "src.api.app:app",
            host=api_config.server.host,
            port=api_config.server.port,
            reload=api_config.server.reload,
        )
    except (Exception, KeyboardInterrupt) as e:
        print(f"Error creating application: {e}")
        print("Exiting gracefully...")
        sys.exit(1)
