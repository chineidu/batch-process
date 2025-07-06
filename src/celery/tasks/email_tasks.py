import time
from datetime import datetime
from typing import Any

import numpy as np

from schemas import EmailSchema
from schemas.db_models import EmailLog, get_db_session
from src import create_logger
from src.celery import celery_app

logger = create_logger()

rng = np.random.default_rng(42)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def send_email(recipient: str, subject: str, body: str) -> dict[str, Any]:
    """Send an email to a recipient with the given subject and body.

    Parameters
    ----------
    recipient : str
        The email address of the recipient.
    subject : str
        The subject line of the email.
    body : str
        The content of the email message.

    Returns
    -------
    dict[str, Any]
        A dictionary containing the email log details with output fields.

    Raises
    ------
    Exception
        If there is an error during the email sending process.
    """
    try:
        data: dict[str, str] = {"recipient": recipient, "subject": subject, "body": body}
        data_dict: dict[str, Any] = EmailSchema(**data).to_data_model_dict()  # type: ignore
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

        # Update email log with sent time
        email_log.sent_at = datetime.now()  # type: ignore
        email_log.status = "sent"

        logger.info(f" [+] Email sent to {recipient}")
        return {key: getattr(email_log, key) for key in email_log.output_fields()}  # type: ignore

    except Exception as e:
        logger.error(f" [x] Error sending email: {e}")
        return {}
