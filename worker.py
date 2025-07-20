from src import create_logger
from src.celery_pkg import celery_app
from src.config import app_settings
from src.database import init_db

logger = create_logger(name="worker")
CELERY_WORKER_TYPE: str = app_settings.CELERY_WORKER_TYPE


def run_worker() -> None:
    """Run the Celery worker."""

    # Initialize database
    init_db()

    # Start worker
    if CELERY_WORKER_TYPE == "light":
        celery_app.worker_main([
            "worker",
            "--loglevel=info",
            "--concurrency=4",
            "--queues=email,data,periodic,celery",
            "--hostname=worker@%h",
        ])
    else:
        celery_app.worker_main([
            "worker",
            "--loglevel=info",
            "--concurrency=4",
            "--queues=prediction",
            "--hostname=worker@%h",
        ])


if __name__ == "__main__":
    run_worker()
