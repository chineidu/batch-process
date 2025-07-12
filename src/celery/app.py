from celery import Celery
from config import app_config
from config.settings import refresh_settings

settings = refresh_settings()

DATABASE_URL = (
    f"db+postgresql://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD.get_secret_value()}"
    f"@localhost:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"
)


def create_celery_app() -> Celery:
    """Create and configure a Celery application instance.

    This function initializes a new Celery application with specific configuration
    settings.

    Returns
    -------
    Celery
        Configured Celery application instance ready for task processing.
    """
    celery = Celery("celery_project")

    # Configuration
    celery.conf.update(
        # DB result backend config
        result_backend=DATABASE_URL,
        result_backend_always_retry=app_config.celery_config.other_config.result_backend_always_retry,
        result_persistent=app_config.celery_config.other_config.result_persistent,
        result_backend_max_retries=app_config.celery_config.other_config.result_backend_max_retries,
        result_expires=app_config.celery_config.other_config.result_expires,
        # Broker config
        broker_url=app_config.celery_config.broker_url,
        # Task config
        task_serializer=app_config.celery_config.task_config.task_serializer,
        result_serializer=app_config.celery_config.task_config.result_serializer,
        timezone=app_config.celery_config.task_config.timezone,
        enable_utc=app_config.celery_config.task_config.enable_utc,
        task_compression=app_config.celery_config.other_config.task_compression,
        # Task routing
        task_routes=app_config.celery_config.task_routes,
        # Beat schedule
        beat_schedule=app_config.celery_config.beat_config.beat_schedule,
        # Worker config
        worker_prefetch_multiplier=app_config.celery_config.worker_config.worker_prefetch_multiplier,
        worker_max_tasks_per_child=app_config.celery_config.worker_config.worker_max_tasks_per_child,
        task_acks_late=app_config.celery_config.worker_config.task_acks_late,
        result_compression=app_config.celery_config.other_config.result_compression,
    )

    # Task discovery
    celery.autodiscover_tasks([
        "src.celery.tasks.email_tasks",
        "src.celery.tasks.data_processing",
        # "src.celery.tasks.periodic_tasks",
    ])

    return celery


celery_app = create_celery_app()
