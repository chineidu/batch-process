import multiprocessing as mp
import sys

# Set spawn method before any other imports that might use CUDA
# CUDA works best with the 'spawn' start method
if mp.get_start_method(allow_none=True) != "spawn":
    mp.set_start_method("spawn", force=True)

from src.celery_app.app import celery_app
from src.config import app_config
from src.db.models import init_db
from src.utilities import create_logger
from src.utilities.model_utils import log_gpu_info

logger = create_logger(name="worker")


def run_worker() -> None:
    """Run the Celery worker."""

    try:
        logger.info("Initializing database...")
        init_db()
        logger.info("Database initialized successfully.")

        log_gpu_info()

        # Configure worker arguments for CUDA compatibility
        argv = [
            "worker",
            "--loglevel=warning",
            f"--concurrency={app_config.model.num_workers}",
            f"--queues={app_config.queues.ml},{app_config.queues.cleanups},{app_config.queues.notifications},celery",
            "--hostname=worker@%h",
            "--pool=threads",
            "--without-gossip",
            "--without-mingle",
            "--without-heartbeat",
        ]

        logger.info(f"Starting Celery worker with args: {' '.join(argv)}")
        logger.info(f"Multiprocessing start method: {mp.get_start_method()}")

        celery_app.worker_main(argv=argv)

    except KeyboardInterrupt:
        logger.info("Worker interrupted by user")
        sys.exit(0)

    except Exception as e:
        logger.error(f"Failed to start Celery worker: {e}")
        logger.exception("Full traceback:")
        sys.exit(1)


if __name__ == "__main__":
    run_worker()
