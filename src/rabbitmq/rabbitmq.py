from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any, Callable, Coroutine

from aio_pika import ExchangeType, IncomingMessage, Message, connect_robust
from aio_pika.abc import AbstractChannel, AbstractExchange, AbstractRobustConnection

from config import app_settings
from schemas import PersonSchema
from src import create_logger

logger = create_logger(name="RMQ_manager")

ConnectionCoroutine = Coroutine[Any, Any, AbstractRobustConnection]


class RabbitMQManager:
    """RabbitMQ Singleton class for handling RabbitMQ operations."""

    _instance: None | RabbitMQManager = None
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
            # Prevents RMQ from sending more than one message to a worker at a time.
            await self.channel.set_qos(prefetch_count=1)

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
            message_data: bytes = message.model_dump_json(by_alias=True).encode("utf-8")
            rmq_message: Message = Message(
                body=message_data,
                content_type="application/json",
                content_encoding="utf-8",
                expiration=app_settings.RABBITMQ_EXPIRATION_MS,
                timestamp=datetime.now(),
            )
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
        async def on_message_callback(message: IncomingMessage) -> None:
            """Callback function to handle incoming messages."""
            async with message.process():  # type: ignore
                message_data: dict[str, Any] = json.loads(message.body.decode("utf-8"))  # type: ignore
                await callback(message_data)  # type: ignore

        try:
            queue = await self.channel.declare_queue(  # type: ignore
                name=app_settings.RABBITMQ_DIRECT_EXCHANGE,
                durable=True,
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


rabbitmq_manager: RabbitMQManager = RabbitMQManager()
