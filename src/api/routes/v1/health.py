from fastapi import APIRouter, status

from src.config import app_config
from src.schemas import HealthCheck

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthCheck, status_code=status.HTTP_200_OK)
async def health_check() -> HealthCheck:
    """
    Simple health check endpoint to verify API is operational.

    Returns:
        HealthCheck: Status of the API
    """

    return HealthCheck(status=app_config.api_config.status, version=app_config.api_config.version)
