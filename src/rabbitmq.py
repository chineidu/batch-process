import json
import time
from typing import Any

import pika

from src.config import app_settings
from src.utilities import create_logger

logger = create_logger(name="rabbitmq")
logger.propagate = False  # This prevents double logging to the root logger


def publish_message_sync(
    payload: dict[str, Any],
    queue_name: str,
    run_id: str,
    event_type: str = "default",
    exchange: str = "",
    routing_key: str = "",
) -> bool:
    """
    Publishes a message to RabbitMQ with exponential backoff on failure.

    This function is designed to be used for synchronous publishing of messages.
    It will retry publishing a message up to `max_retry_attempts` times with an
    exponential backoff of `retry_delay` seconds between attempts.

    Parameters
    ----------
    payload : dict
        The message body to be published.
    queue_name : str
        The name of the queue to publish to.
    run_id : str
        The run ID to include in the message headers.
    event_type : str, optional
        The type of event to include in the message headers.
    exchange : str, optional
        The name of the exchange to publish to.
    routing_key : str, optional
        The routing key to use for publishing.

    Returns
    -------
    bool
        True if the message was published successfully, False otherwise.
    """
    max_retry_attempts: int = 3
    retry_delay: float = 2.0  # seconds
    backoff_factor: float = 2.0

    for attempt in range(max_retry_attempts):
        connection = None
        channel = None
        try:
            # Create fresh connection for each attempt to avoid state issues
            connection_params = pika.URLParameters(app_settings.rabbitmq_url)
            connection_params.connection_attempts = 1  # Don't retry at connection level
            connection_params.retry_delay = 1
            connection_params.socket_timeout = 10
            connection_params.heartbeat = 0  # Disable heartbeat for short-lived connections

            connection = pika.BlockingConnection(connection_params)
            channel = connection.channel()

            # Enable publisher confirms for reliability
            channel.confirm_delivery()

            # Declare queue
            channel.queue_declare(queue=queue_name, durable=True)

            # Prepare message
            message_body: str = json.dumps(payload, ensure_ascii=False)

            # Set routing key if not provided
            if not routing_key:
                routing_key = queue_name

            # Publish message - when confirms are enabled, this will block until confirmed
            try:
                channel.basic_publish(
                    exchange=exchange,
                    routing_key=routing_key,
                    body=message_body,
                    properties=pika.BasicProperties(
                        content_type="application/json",
                        delivery_mode=2,  # Make message persistent
                        timestamp=int(time.time()),
                        headers={
                            "producer": "ner-task",
                            "run_id": run_id,
                            "event_type": event_type,
                            "attempt": attempt + 1,
                        },
                    ),
                    mandatory=True,  # Ensure message is routable
                )
                return True

            except pika.exceptions.UnroutableError:  # type: ignore
                raise

        except Exception as e:
            logger.error(f"[x] Error publishing message for run_id {run_id} on attempt {attempt + 1}: {e}")
            if attempt < max_retry_attempts - 1:
                time.sleep(retry_delay)
                retry_delay *= backoff_factor  # Exponential backoff
                continue
            raise Exception(f"Failed to publish message after {max_retry_attempts} attempts: {str(e)}") from e

        # Close channel and connection
        finally:
            try:
                if channel and not channel.is_closed:
                    channel.close()
            except Exception as e:
                logger.warning(f"[!] Error closing channel for run_id {run_id}: {e}")

            try:
                if connection and not connection.is_closed:
                    connection.close()
            except Exception as e:
                logger.warning(f"[!] Error closing connection for run_id {run_id}: {e}")

    logger.error(f"[x] All publish attempts failed for run_id: {run_id}")
    return False

