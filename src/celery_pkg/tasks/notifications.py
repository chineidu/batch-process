"""This module is for publishing processed messages to any queue that can be consumed by any consumer."""

import json
import time
from typing import Any

import pika
from celery import shared_task

from src.celery_app import BaseCustomTask, MLTask, celery_app
from src.config import app_settings
from src.utilities import create_logger

logger = create_logger(name="notifications")
logger.propagate = False  # This prevents double logging to the root logger


@shared_task(bind=True, base=BaseCustomTask)
def publish_to_queue(
    self,  # noqa: ANN001
    payload: dict[str, Any],
    queue_name: str,
    exchange: str = "",
    routing_key: str = "",
) -> None:
    """
    Publish a message to a RabbitMQ queue.

    Parameters
    ----------
    payload : dict[str, Any]
        The message payload to publish.
    queue_name : str
        The name of the queue to publish to.
    exchange : str, optional
        The exchange to use for publishing the message. Defaults to an empty string.
    routing_key : str, optional
        The routing key to use for publishing the message. Defaults to an empty string.

    Raises
    ------
    Exception
        If any exception occurs while publishing the message.

    """
    try:
        # Create connection, channel, and declare queue
        connection = pika.BlockingConnection(pika.URLParameters(url=app_settings.rabbitmq_url))
        channel = connection.channel()

        # Declare queue
        channel.queue_declare(queue=queue_name, durable=True)
        # Decompress message
        message_body: str = json.dumps(payload, ensure_ascii=False)

        # Publish message
        channel.basic_publish(
            exchange=exchange,
            routing_key=routing_key,
            body=message_body,
            properties=pika.BasicProperties(
                content_type="application/json",
                delivery_mode=2,  # Make message persistent
                timestamp=int(time.time()),
                headers={"producer": "ner-task"},
            ),
        )
        logger.warning(f"[+] Published message to queue {queue_name}")
        connection.close()
    except pika.exceptions.AMQPConnectionError as e:  # type: ignore
        logger.error(f"[x] Failed to connect to RabbitMQ: {e}")
        raise self.retry(exc=e) from e
    except pika.exceptions.AMQPChannelError as e:  # type: ignore
        logger.error(f"Failed to create channel: {e}")
        raise self.retry(exc=e) from e
    except pika.exceptions.AMQPQueueError as e:  # type: ignore
        logger.error(f"[x] Failed to declare queue: {e}")
        raise self.retry(exc=e) from e
    except Exception as e:
        logger.error(f"[x] Unexpected error occurred: {e}")
        raise self.retry(exc=e) from e


# celery_app was used and not shared_task to ensure that the result backend is inherited.
@celery_app.task(bind=True, base=MLTask)
def health_check_task(self) -> dict[str, Any]:  # noqa: ANN001
    """Health check task to verify model is loaded and ready.

    Returns
    -------
    dict[str, Any]
        Health check results
    """
    try:
        model_info: dict[str, Any] = self.model_manager.get_model_info()

        return {
            "status": "healthy",
            "model_info": model_info,
            "timestamp": time.time(),
        }

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": time.time(),
        }

