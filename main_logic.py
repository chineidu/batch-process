import time
from notebooks.app.celery_app import celery_app

# Continue with your main logic
from config. import init_db
from notebooks.app.tasks import send_email, send_bulk_emails, process_large_dataset

def main():
    # Initialize database
    print("Initializing database...")
    init_db()
    
    # Example 1: Send a single email
    print("\n1. Sending single email...")
    result = send_email.delay(
        recipient="user@example.com",
        subject="Test Email",
        body="This is a test email from Celery!"
    )
    print(f"Task ID: {result.id}")
    print(f"Result: {result.get(timeout=30)}")
    
    # Example 2: Send bulk emails
    print("\n2. Sending bulk emails...")
    emails = [
        {"recipient": f"user{i}@example.com", "subject": f"Bulk Email {i}", "body": f"Message {i}"}
        for i in range(5)
    ]
    bulk_result = send_bulk_emails.delay(emails)
    print(f"Bulk email result: {bulk_result.get(timeout=60)}")