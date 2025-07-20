from typing import Literal

from dotenv import load_dotenv
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Settings class for managing application configuration.
    """

    model_config = SettingsConfigDict(env_file=".env")

    # ======= Environment =======
    ENVIRONMENT: Literal["dev", "prod", "test"]

    # ======= RabbitMQ settings =======
    RABBITMQ_HOST: str = "localhost"
    RABBITMQ_PORT: int = 5672
    RABBITMQ_DEFAULT_USER: str
    RABBITMQ_DEFAULT_PASS: SecretStr
    RABBITMQ_EXPIRATION_MS: int = 3_600_000  # 60 minutes
    RABBITMQ_HEARTBEAT: int = 600

    # ======= Database settings =======
    POSTGRES_USER: str
    POSTGRES_PASSWORD: SecretStr
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int
    POSTGRES_DB: str

    # ======= Celery settings =======
    CELERY_FLOWER_USER: str
    CELERY_FLOWER_PASSWORD: SecretStr
    CELERY_WORKER_TYPE: Literal["light", "heavy"] = "light"

    @property
    def rabbitmq_url(self) -> str:
        """
        Constructs the RabbitMQ connection URL.

        Returns
        -------
        str
            Complete RabbitMQ connection URL in the format:
            amqp://user:password@host:port/
        """
        return (
            f"amqp://{self.RABBITMQ_DEFAULT_USER}:{self.RABBITMQ_DEFAULT_PASS.get_secret_value()}"
            f"@{self.RABBITMQ_HOST}:{self.RABBITMQ_PORT}/?heartbeat={self.RABBITMQ_HEARTBEAT}"
        )

    @property
    def celery_database_url(self) -> str:
        """
        Constructs the PostgreSQL connection URL.

        Returns
        -------
        str
            Complete PostgreSQL connection URL in the format:
            db+postgresql://user:password@host:port/dbname
        """
        return (
            f"db+postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD.get_secret_value()}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def database_url(self) -> str:
        """
        Constructs the PostgreSQL connection URL.

        Returns
        -------
        str
            Complete PostgreSQL connection URL in the format:
            postgresql+psycopg2://user:password@host:port/dbname
        """

        return (
            f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD.get_secret_value()}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )


def refresh_settings() -> Settings:
    """Refresh environment variables and return new Settings instance.

    This function reloads environment variables from .env file and creates
    a new Settings instance with the updated values.

    Returns
    -------
    Settings
        A new Settings instance with refreshed environment variables
    """
    load_dotenv(override=True)
    return Settings()  # type: ignore


app_settings: Settings = refresh_settings()
