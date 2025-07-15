# app/tasks/periodic_tasks.py
from datetime import datetime, timedelta
from typing import Any

from src import create_logger
from src.celery import celery_app
from src.database import get_db_session
from src.database.db_models import BaseTask, CeleryTasksLog, DataProcessingJob, EmailLog, TaskResult

logger = create_logger(name="periodic_tasks")


@celery_app.task
def cleanup_old_records() -> dict[str, Any]:
    """
    Clean up old records from the database
    """
    try:
        cutoff_date = datetime.now() - timedelta(days=30)

        with get_db_session() as session:
            # === Clean up old task results: Get count and delete ===
            old_tasks = session.query(TaskResult).where(TaskResult.created_at < cutoff_date).count()
            session.query(TaskResult).where(TaskResult.created_at < cutoff_date).delete()

            # === Clean up old task results: Get count and delete ===
            old_emails = session.query(EmailLog).where(EmailLog.created_at < cutoff_date).count()
            session.query(EmailLog).where(EmailLog.created_at < cutoff_date).delete()

            # === Clean up old task results: Get count and delete ===
            old_jobs = session.query(DataProcessingJob).where(DataProcessingJob.created_at < cutoff_date).count()
            session.query(DataProcessingJob).where(DataProcessingJob.created_at < cutoff_date).delete()

            logger.info(f"Cleaned up {old_tasks} task results, {old_emails} email logs, {old_jobs} processing jobs")

            return {
                "status": "completed",
                "cleaned_up": {"task_results": old_tasks, "email_logs": old_emails, "processing_jobs": old_jobs},
            }

    except Exception as exc:
        logger.error(f"Error during cleanup: {exc}")
        raise


@celery_app.task(bind=True, base=BaseTask)
def health_check(self) -> dict[str, Any] | dict[str, str]:  # noqa: ANN001, ARG001
    """
    Perform system health check
    """
    try:
        with get_db_session() as session:
            # Check database connectivity
            from sqlalchemy import text

            session.execute(text("SELECT 1"))

            # Get some statistics
            total_tasks = (
                session.query(CeleryTasksLog).where(CeleryTasksLog.task_name.not_like(r"%health_check%")).count()
            )
            recent_emails = (
                session.query(EmailLog).where(EmailLog.created_at > (datetime.now() - timedelta(hours=24))).count()
            )
            active_jobs = session.query(DataProcessingJob).where(DataProcessingJob.status == "pending").count()

            logger.info("Health check completed successfully")

            return {
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "stats": {
                    "total_tasks": total_tasks,
                    "recent_emails_24h": recent_emails,
                    "active_processing_jobs": active_jobs,
                },
            }

    except Exception as exc:
        logger.error(f"Health check failed: {exc}")
        return {"status": "unhealthy", "error": str(exc), "timestamp": datetime.now().isoformat()}
