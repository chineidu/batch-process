import time
from datetime import datetime
from typing import Any

import numpy as np

from celery import group
from schemas import EmailSchema
from src import create_logger
from src.celery import celery_app
from src.database import get_db_session
from src.database.db_models import BaseTask, EmailLog

logger = create_logger()

rng = np.random.default_rng(42)


# Note: When `bind=True`, celery automatically passes the task instance as the first argument
# meaning that we need to use `self` and this provides additional functionality like retries, etc
@celery_app.task(bind=True, base=BaseTask)
def send_email(self, recipient: str, subject: str, body: str) -> dict[str, Any]:  # noqa: ANN001, ARG001
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
    data: dict[str, Any] = {
        "recipient": recipient,
        "subject": subject,
        "body": body,
    }
    data_dict: dict[str, Any] = EmailSchema(**data).model_dump()
    email_id: int | None = None

    try:
        with get_db_session() as db:
            email_log = EmailLog(**data_dict)
            db.add(email_log)
            db.flush()
            email_id = email_log.id
    except Exception as e:
        logger.error(f" [x] Error logging email: {e}")
        # Trigger retry
        raise self.retry(exc=e) from e

    try:
        # Simulate email sending process
        time.sleep(2)

        # Update successful task with sent time
        sent_at = datetime.now()
        status = "success"
        if email_id is not None:
            try:
                with get_db_session() as db:
                    db.query(EmailLog).where(EmailLog.id == email_id).update({
                        EmailLog.sent_at: sent_at,
                        EmailLog.status: status,
                    })
            except Exception as db_error:
                logger.error(f" [x] Error updating email status in database: {db_error}")
                raise self.retry(exc=db_error) from db_error

            logger.info(f" [+] Email sent to {data_dict.get('recipient')}")

        return {
            "status": status,
            "recipient": data_dict.get("recipient"),
            "subject": data_dict.get("subject"),
            "sent_at": sent_at.isoformat(),
        }

    except Exception as e:
        logger.error(f" [x] Error sending email: {e}")
        raise self.retry(exc=e, countdown=5) from e


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
    """
    job = group(send_email.s(email["recipient"], email["subject"], email["body"]) for email in emails)
    # Dispatch the tasks asynchronously
    result = job.apply_async()

    return {"status": "dispatched", "total_emails": len(emails), "group_id": result.id}
