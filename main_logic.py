import json
from typing import Any

from src import create_logger
from src.celery.tasks import ml_process_large_dataset

logger = create_logger(name="main")

fp: str = "data/sample_data.jsonl"
with open(fp, "r") as f:
    data: list[dict[str, Any]] = [json.loads(line) for line in f]


def main() -> None:
    """Main function to run the Celery tasks."""

    # ===== Example 0: Process large dataset =====
    logger.info("\n0. Processing large dataset...")
    try:
        num_chunks: int = 5
        result = ml_process_large_dataset.delay(data, num_chunks)
        logger.info(f"Task ID: {result.id}")
    except Exception as e:
        logger.error(f"Task failed with error: {e}")
        logger.error(f"Task state: {result.state}")
        if hasattr(result, "traceback"):
            logger.error(f"Traceback: {result.traceback}")

    # # ====== Example 1: Send a single email ======
    # logger.info("\n1. Sending single email...")
    # result = send_email.delay(
    #     recipient="user@example.com",
    #     subject="Test Email",
    #     body="This is a test single email from Celery!",
    # )
    # logger.info(f"Task ID: {result.id}")
    # try:
    #     task_result = result.get(timeout=30)
    #     logger.info(f"Result: {task_result}")
    # except Exception as e:
    #     logger.error(f"Task failed with error: {e}")
    #     logger.error(f"Task state: {result.state}")
    #     if hasattr(result, "traceback"):
    #         logger.error(f"Traceback: {result.traceback}")

    # # ===== Example 2: Send emails in bulk ======
    # logger.info("\n2. Sending bulk emails...")
    # emails = [
    #     {"recipient": f"user{i}@example.com", "subject": f"Bulk Email {i}", "body": f"Message {i}"} for i in range(5)
    # ]
    # bulk_result = send_bulk_emails.delay(emails)
    # logger.info(f"Bulk email result: {bulk_result.get(timeout=60)}")

    # # ====== Example 3: Process large dataset ======
    # logger.info("\n3. Processing large dataset...")
    # large_data = list(range(100)) + [f"string_{i}" for i in range(80)]
    # processing_result = process_large_dataset.delay(large_data, chunk_size=15)
    # logger.info(f"Processing result: {processing_result.get(timeout=120)}")

    # logger.info("All tasks completed!")


if __name__ == "__main__":
    main()
