import time
from datetime import datetime
from typing import Any

import numpy as np
from sqlalchemy import select

from celery import group
from schemas import EmailSchema
from schemas.db_models import EmailLog, get_db_session
from src import create_logger
from src.celery import celery_app

logger = create_logger()

rng = np.random.default_rng(42)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def send_email(data: dict[str, Any]) -> dict[str, Any]:
    """Send an email to a recipient with the given subject and body.

    Parameters
    ----------
    data : dict[str, Any]
        A dictionary containing the email details, including recipient, subject, and body.

    Returns
    -------
    dict[str, Any]
        A dictionary containing the email log details with output fields.

    Raises
    ------
    Exception
        If there is an error during the email sending process.
    """
    data_dict: dict[str, Any] = EmailSchema(**data).to_data_model_dict()  # type: ignore

    try:
        with get_db_session() as db:
            email_log = EmailLog(**data_dict)
            db.add(email_log)
            db.flush()

        # Simulate email sending process
        time.sleep(2)

        # Simulate email sending failure
        if rng.random() < 0.3:
            # Update email log
            email_log.sent_at = datetime.now()  # type: ignore
            email_log.status = "failed"
            logger.error("Email sending failed")
            return {key: getattr(email_log, key) for key in email_log.output_fields()}  # type: ignore

        # Update email log with sent time
        email_log.sent_at = datetime.now()  # type: ignore
        email_log.status = "sent"

        logger.info(f" [+] Email sent to {data_dict.get('recipient')}")
        return {key: getattr(email_log, key) for key in email_log.output_fields()}  # type: ignore

    except Exception as e:
        with get_db_session() as db:
            statement = select(EmailLog).filter_by(
                recipient=data_dict.get("recipient"),
                subject=data_dict.get("subject"),
                created_at=data_dict.get("created_at"),
            )
            email_log = db.execute(statement).scalar_one()
            # Update email log
            email_log.sent_at = datetime.now()  # type: ignore
            email_log.status = "failed"
        logger.error(f" [x] Error sending email: {e}")
        return {key: getattr(email_log, key) for key in email_log.output_fields()}  # type: ignore


@celery_app.task
def send_bulk_emails(emails: list[dict[str, str]]) -> dict[str, Any]:
    """Send multiple emails asynchronously using Celery tasks.

    Parameters
    ----------
    emails : list[dict[str, str]]
        A list of dictionaries containing email data. Each dictionary should contain
        email parameters like recipient, subject, body, etc.

    Returns
    -------
    dict[str, Any]
        A dictionary containing:
        - status : str
            Status of the bulk email dispatch
        - total_emails : int
            Number of emails to be sent
        - group_id : str
            Unique identifier for the group of email tasks
            
    """
    job = group(send_email.s(email) for email in emails)
    result = job.apply_async()

    return {"status": "dispatched", "total_emails": len(emails), "group_id": result.id}
