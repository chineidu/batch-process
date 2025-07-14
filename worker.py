from schemas.db_models import init_db
from src import create_logger
from src.celery import celery_app

logger = create_logger(name="worker")


def run_worker() -> None:
    """Run the Celery worker."""

    # Initialize database
    logger.info("Initializing database...")
    init_db()

    # Start worker
    celery_app.worker_main([
        "worker",
        "--loglevel=info",
        "--concurrency=4",
        "--queues=email,data,periodic,celery",
        "--hostname=worker@%h",
    ])


if __name__ == "__main__":
    run_worker()
