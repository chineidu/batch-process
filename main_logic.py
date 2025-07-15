from typing import Any

from src import create_logger
from src.celery.tasks import process_large_dataset, send_bulk_emails, send_email

logger = create_logger(name="main")


def main() -> None:
    """Main function to run the Celery tasks."""

    # ====== Example 1: Send a single email ======
    logger.info("\n1. Sending single email...")
    result = send_email.delay(
        recipient="user@example.com",
        subject="Test Email",
        body="This is a test single email from Celery!",
    )
    logger.info(f"Task ID: {result.id}")
    try:
        task_result = result.get(timeout=30)
        logger.info(f"Result: {task_result}")
    except Exception as e:
        logger.error(f"Task failed with error: {e}")
        logger.error(f"Task state: {result.state}")
        if hasattr(result, "traceback"):
            logger.error(f"Traceback: {result.traceback}")

    # ===== Example 2: Send emails in bulk ======
    logger.info("\n2. Sending bulk emails...")
    emails = [
        {"recipient": f"user{i}@example.com", "subject": f"Bulk Email {i}", "body": f"Message {i}"}
        for i in range(5)
    ]
    bulk_result = send_bulk_emails.delay(emails)
    logger.info(f"Bulk email result: {bulk_result.get(timeout=60)}")

    # ====== Example 3: Process large dataset ======
    logger.info("\n3. Processing large dataset...")
    large_data = list(range(100)) + [f"string_{i}" for i in range(50)]
    processing_result = process_large_dataset.delay(large_data, chunk_size=15)
    logger.info(f"Processing result: {processing_result.get(timeout=120)}")

    logger.info("All tasks completed!")


if __name__ == "__main__":
    main()
