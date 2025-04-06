from __future__ import annotations

from datetime import datetime
import json
import os
from typing import Any, Callable, Coroutine

from aio_pika import IncomingMessage, connect_robust, ExchangeType, Message
from aio_pika.abc import AbstractChannel, AbstractExchange, AbstractRobustConnection

from schemas import PersonSchema
from src import create_logger
from config import app_settings

logger = create_logger(name=__name__)

ConnectionCoroutine = Coroutine[Any, Any, AbstractRobustConnection]


class RabbitMQManager:
    """RabbitMQ Singleton class for handling RabbitMQ operations."""

    _instance: None = None
    _initialized: bool = False

    def __new__(cls) -> RabbitMQManager:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if not RabbitMQManager._initialized:
            self.connection: AbstractRobustConnection | None = None
            self.channel: AbstractChannel | None = None
            self.direct_exchange: AbstractExchange | None = None
            self.process_id: int = os.getpid()
            logger.info(
                f" [+] Initializing {self.__class__.__name__} with PID: {self.process_id}"
            )
            RabbitMQManager._initialized = True

    async def connect(self) -> bool:
        try:
            self.connection = await connect_robust(
                url=app_settings.rabbitmq_url,
                client_properties={
                    "connection_name": f"PythonProducer_{self.process_id}"
                },
            )
            logger.info(
                f" [+] Process-{self.process_id} Connected to {self.__class__.__name__}"
            )
            self.channel = await self.connection.channel()

            # Declare the exchange
            self.direct_exchange = await self.channel.declare_exchange(
                name=app_settings.RABBITMQ_DIRECT_EXCHANGE,
                type=ExchangeType.DIRECT,
                durable=True,
            )
            logger.info(
                f" [+] Process-{self.process_id} Declared Exchange: {app_settings.RABBITMQ_DIRECT_EXCHANGE!r}"
            )
            return True
        except Exception as e:
            logger.error(f" [x] Error connecting to {self.__class__.__name__}: {e}")
            return False

    async def close(self) -> None:
        if self.connection:
            await self.connection.close()
            logger.info(
                f" [+] Process-{self.process_id} closed {self.__class__.__name__}"
            )

    async def publish(self, message: PersonSchema) -> bool:
        try:
            message_data: dict[str, Any] = message.model_dump_json(
                by_alias=True
            ).encode("utf-8")
            rmq_message: Message = Message(
                body=message_data,
                content_type="application/json",
                content_encoding="utf-8",
                expiration=app_settings.RABBITMQ_EXPIRATION_MS,
                timestamp=datetime.now(),
            )
            await self.direct_exchange.publish(
                message=rmq_message,
                routing_key=app_settings.RABBITMQ_DIRECT_EXCHANGE,
            )
            logger.info(
                f" [+] Process-{self.process_id} Published message to {app_settings.RABBITMQ_DIRECT_EXCHANGE}"
            )
            return True
        except Exception as e:
            logger.error(f" [x] Error publishing message: {e}")
            return False

    async def consume(self, callback: Callable[[IncomingMessage], Coroutine]) -> bool:
        async def on_message_callback(message: str) -> None:
            """Callback function to handle incoming messages."""
            async with message.process():
                message_data: dict[str, Any] = json.loads(message.body.decode("utf-8"))
                await callback(message_data)

        try:
            queue = await self.channel.declare_queue(
                name=app_settings.RABBITMQ_DIRECT_EXCHANGE,
                durable=True,
            )
            await queue.bind(
                self.direct_exchange, routing_key=app_settings.RABBITMQ_DIRECT_EXCHANGE
            )
            await queue.consume(on_message_callback)
            logger.info(
                f" [+] Process-{self.process_id} Consuming messages from {app_settings.RABBITMQ_DIRECT_EXCHANGE!r}"
            )
        except Exception as e:
            logger.error(f" [x] Error consuming messages: {e}")
            return False


rabbitmq_manager: RabbitMQManager = RabbitMQManager()
