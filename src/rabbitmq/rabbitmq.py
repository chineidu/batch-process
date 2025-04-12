from __future__ import annotations

import asyncio
import json
import os
from datetime import datetime
from typing import Any, Callable, Coroutine

from aio_pika import ExchangeType, IncomingMessage, Message, connect_robust
from aio_pika.abc import (
    AbstractChannel,
    AbstractExchange,
    AbstractQueue,
    AbstractRobustConnection,
)

from config import app_settings
from schemas import MultiPersonsSchema, PersonSchema
from src import create_logger

logger = create_logger(name="RMQ_manager")

ConnectionCoroutine = Coroutine[Any, Any, AbstractRobustConnection]


class RabbitMQManager:
    """RabbitMQ Singleton class for handling RabbitMQ operations."""

    _instance: None | RabbitMQManager = None
    _initialized: bool = False

    def __new__(cls) -> RabbitMQManager:
        """Create or return the singleton instance of RabbitMQManager."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if not RabbitMQManager._initialized:
            self.connection: AbstractRobustConnection | None = None
            self.channel: AbstractChannel | None = None
            self.direct_exchange: AbstractExchange | None = None
            self.process_id: int = os.getpid()
            logger.info(f" [+] Initializing {self.__class__.__name__} with PID: {self.process_id}")
            RabbitMQManager._initialized = True

    async def connect(
        self,
        max_attempts: int = 5,
        initial_delay: float = 1.0,
        backoff_factor: float = 2.0,
    ) -> bool:
        """Connect to RabbitMQ and declare the exchange and queue.

        Parameters
        -----------
            max_attempts (int): The maximum number of attempts to connect.
            initial_delay (float): The initial delay between attempts.
            backoff_factor (float): The factor to multiply the delay by for each attempt.

        Returns
        --------
            bool: True if the connection was successful, False otherwise.
        """
        delay: float = initial_delay
        attempt: int = 0

        while attempt < max_attempts:
            try:
                logger.info(
                    f"Attempting to connect to RabbitMQ with host and port: "
                    f"{app_settings.RABBITMQ_HOST}:{app_settings.RABBITMQ_PORT}"
                )
                # Connect to RabbitMQ
                self.connection = await connect_robust(
                    url=app_settings.rabbitmq_url,
                    client_properties={"connection_name": f"PythonProducer_{self.process_id}"},
                    timeout=5,
                )
                logger.info(
                    f" [+] Process-{self.process_id} Connected to {self.__class__.__name__}"
                )

                # Create channel and set QoS
                self.channel = await self.connection.channel()
                # It prevents RMQ from sending more than one message to a consumer at a time.
                await self.channel.set_qos(prefetch_count=1)

                # Declare the exchange and queue for dead letter
                self.dl_exchange = await self.channel.declare_exchange(
                    name=f"{app_settings.RABBITMQ_DIRECT_EXCHANGE}.dlx",
                    type=ExchangeType.DIRECT,
                    durable=True,
                )
                self.dl_queue: AbstractQueue = await self.channel.declare_queue(
                    name=f"{app_settings.RABBITMQ_DIRECT_EXCHANGE}.dlq",
                    durable=True,
                )
                # Bind the queue to the exchange
                await self.dl_queue.bind(
                    self.dl_exchange, routing_key=app_settings.RABBITMQ_DIRECT_EXCHANGE
                )
                # Declare the exchange
                self.direct_exchange = await self.channel.declare_exchange(
                    name=app_settings.RABBITMQ_DIRECT_EXCHANGE,
                    type=ExchangeType.DIRECT,
                    durable=True,
                )

                logger.info(
                    f" [+] Process-{self.process_id} "
                    f"Declared Exchange: {app_settings.RABBITMQ_DIRECT_EXCHANGE!r}"
                )
                return True

            except Exception as e:
                attempt += 1
                if attempt >= max_attempts:
                    logger.error(f" [!] Failed to connect to RabbitMQ: {e}")
                    return False

                logger.error(f"Connection attempt {attempt} failed: {e}. Retrying in {delay}s... ")
                await asyncio.sleep(delay)
                delay *= backoff_factor

        # This should never be reached if the loop exits properly
        return False

    async def close(self) -> None:
        """Close the RabbitMQ connection."""
        try:
            if self.channel and not self.channel.is_closed:
                await self.channel.close()

            if self.connection and not self.connection.is_closed:
                await self.connection.close()
            logger.info(f" [+] Process-{self.process_id} closed {self.__class__.__name__}")

        except Exception as e:
            logger.error(f" [x] Error closing {self.__class__.__name__}: {e}")

    async def _publish(self, message: PersonSchema | MultiPersonsSchema) -> Message:
        message_data: bytes = message.model_dump_json(by_alias=True).encode("utf-8")
        rmq_message: Message = Message(
            body=message_data,
            content_type="application/json",
            content_encoding="utf-8",
            expiration=app_settings.RABBITMQ_EXPIRATION_MS,
            timestamp=datetime.now(),
        )
        return rmq_message

    async def publish(self, message: PersonSchema) -> bool:
        """Publish a message to RabbitMQ.

        Parameters
        -----------
            message (PersonSchema): The message to publish.

        Returns
        --------
            bool: True if the message was published successfully, False otherwise.
        """
        try:
            rmq_message: Message = await self._publish(message)
            await self.direct_exchange.publish(  # type: ignore
                message=rmq_message,
                routing_key=app_settings.RABBITMQ_DIRECT_EXCHANGE,
            )
            logger.info(
                f" [+] Process-{self.process_id} Published message "
                f"to {app_settings.RABBITMQ_DIRECT_EXCHANGE}"
            )
            return True
        except Exception as e:
            logger.error(f" [x] Error publishing message: {e}")
            return False

    async def batch_publish(self, message: MultiPersonsSchema) -> bool:
        """Publish a message to RabbitMQ.

        Parameters
        -----------
            message (PersonSchema): The message to publish.

        Returns
        --------
            bool: True if the message was published successfully, False otherwise.
        """
        try:
            rmq_message: Message = await self._publish(message)
            await self.direct_exchange.publish(  # type: ignore
                message=rmq_message,
                routing_key=app_settings.RABBITMQ_DIRECT_EXCHANGE,
            )
            logger.info(
                f" [+] Process-{self.process_id} Published message "
                f"to {app_settings.RABBITMQ_DIRECT_EXCHANGE}"
            )
            return True
        except Exception as e:
            logger.error(f" [x] Error publishing message: {e}")
            return False

    async def consume(
        self, callback: Callable[[IncomingMessage], Coroutine[Any, Any, None]]
    ) -> bool:
        """Callback function to handle incoming messages.

        Parameters
        -----------
            callback (Callable[[IncomingMessage], Coroutine[Any, Any, None]]): The callback
            function to handle incoming messages.

        Returns
        --------
            bool: True if the message was consumed successfully, False otherwise.
        """

        async def on_message_callback(message: IncomingMessage) -> None:
            """Callback function to handle incoming messages.

            with requueue=False, the message is not requeued but is routed to
            the dead letter exchange.
            """
            async with message.process(requeue=False):  # type: ignore
                # Msg will be ACKed if the callback function does not raise an exception.
                # If the callback raises an exception, it be be routed to the DL exchange
                message_data: dict[str, Any] = json.loads(message.body.decode("utf-8"))  # type: ignore
                await callback(message_data)  # type: ignore

        try:
            queue: AbstractQueue = await self.channel.declare_queue(  # type: ignore
                name=app_settings.RABBITMQ_DIRECT_EXCHANGE,
                durable=True,
                arguments={
                    "x-dead-letter-exchange": f"{app_settings.RABBITMQ_DIRECT_EXCHANGE}.dlx",
                    "x-dead-letter-routing-key": app_settings.RABBITMQ_DIRECT_EXCHANGE,
                },
            )
            await queue.bind(
                self.direct_exchange,  # type: ignore
                routing_key=app_settings.RABBITMQ_DIRECT_EXCHANGE,  # type: ignore
            )
            await queue.consume(on_message_callback)  # type: ignore
            logger.info(
                f" [+] Process-{self.process_id} Consuming messages "
                f"from {app_settings.RABBITMQ_DIRECT_EXCHANGE!r}"
            )
            return True
        except Exception as e:
            logger.error(f" [x] Error consuming messages: {e}")
            return False

    async def consume_dlq(
        self, callback: Callable[[IncomingMessage], Coroutine[Any, Any, None]]
    ) -> bool:
        """Callback function to handle incoming messages.

        Parameters
        -----------
            callback (Callable[[IncomingMessage], Coroutine[Any, Any, None]]):
            The callback function to handle incoming messages.

        Returns
        --------
            bool: True if the message was consumed successfully, False otherwise.
        """

        async def on_dlq_message_callback(message: IncomingMessage) -> None:
            try:
                async with message.process():  # type: ignore
                    message_data: dict[str, Any] = json.loads(message.body.decode("utf-8"))  # type: ignore
                    await callback(message_data)  # type: ignore
            except Exception as e:
                logger.error(f" [x] Error processing DLQ message: {e}")
                await message.nack(requeue=True)

        try:
            await self.dl_queue.consume(on_dlq_message_callback)  # type: ignore
            logger.info(
                f" [+] Process-{self.process_id} Consuming DLQ messages "
                f"from {app_settings.RABBITMQ_DIRECT_EXCHANGE}.dlq"
            )
            return True
        except Exception as e:
            logger.error(f" [x] Error consuming DLQ messages: {e}")
            return False


rabbitmq_manager: RabbitMQManager = RabbitMQManager()
