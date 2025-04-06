import asyncio

from schemas import PersonSchema
from .rabbitmq import rabbitmq_manager


async def publish_message(message: PersonSchema) -> None:
    await rabbitmq_manager.connect()
    await rabbitmq_manager.publish(message)


if __name__ == "__main__":
    message: PersonSchema = PersonSchema(
        id="p1", sex="male", age=30, pclass=1, sibsp=0, parch=0, fare=80.0, embarked="c"
    )
    asyncio.run(publish_message(message=message))
