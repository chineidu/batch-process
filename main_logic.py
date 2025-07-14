from typing import Any

from schemas.db_models import init_db
from src.celery.tasks import process_large_dataset, send_bulk_emails, send_email


def main() -> None:
    """Main function to run the Celery tasks."""
    # Initialize database
    print("Initializing database...")
    init_db()

    # Example 1: Send a single email
    print("\n1. Sending single email...")
    result = send_email.delay(
        recipient="user@example.com",
        subject="Test Email",
        body="This is a test email from Celery!",
    )
    print(f"Task ID: {result.id}")
    # print(f"Result: {result.get(timeout=30)}")
    try:
        task_result = result.get(timeout=30)
        print(f"Result: {task_result}")
    except Exception as e:
        print(f"Task failed with error: {e}")
        print(f"Task state: {result.state}")
        if hasattr(result, "traceback"):
            print(f"Traceback: {result.traceback}")

    # Example 2: Send  emails
    print("\n2. Sending bulk emails...")
    emails = [
        {"recipient": f"user{i}@example.com", "subject": f"Bulk Email {i}", "body": f"Message {i}"}
        for i in range(5)
    ]
    bulk_result = send_bulk_emails.delay(emails)
    print(f"Bulk email result: {bulk_result.get(timeout=60)}")

    # Example 3: Process large dataset
    print("\n3. Processing large dataset...")
    large_data = list(range(100)) + [f"string_{i}" for i in range(50)]
    processing_result = process_large_dataset.delay(large_data, chunk_size=15)
    print(f"Processing result: {processing_result.get(timeout=120)}")

    print("\nAll tasks completed!")


if __name__ == "__main__":
    main()
