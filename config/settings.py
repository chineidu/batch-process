from dotenv import load_dotenv
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Settings class for managing application configuration.
    """

    model_config = SettingsConfigDict(env_file=".env")

    # RabbitMQ settings
    RABBITMQ_HOST: str = "localhost"
    RABBITMQ_PORT: int = 5672
    RABBITMQ_DEFAULT_USER: str
    RABBITMQ_DEFAULT_PASS: SecretStr
    RABBITMQ_EXPIRATION_MS: int = 3_600_000  # 60 minutes
    RABBITMQ_DIRECT_EXCHANGE: str = "person_exchange"

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
            f"@{self.RABBITMQ_HOST}:{self.RABBITMQ_PORT}/"
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
    return Settings()


app_settings: Settings = refresh_settings()
