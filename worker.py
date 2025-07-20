from src import create_logger
from src.celery_pkg import celery_app
from src.database import init_db

logger = create_logger(name="worker")


def run_worker() -> None:
    """Run the Celery worker."""

    # Initialize database
    init_db()

    # Start worker
    celery_app.worker_main([
        "worker",
        "--loglevel=info",
        "--concurrency=4",
        "--queues=email,data,periodic,celery,prediction",
        "--hostname=worker@%h",
    ])


if __name__ == "__main__":
    run_worker()
