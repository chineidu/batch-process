import re
from typing import Literal
from urllib.parse import quote

from dotenv import load_dotenv
from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def fix_url_credentials(url: str) -> str:
    """
    Fix URL by properly encoding special characters in credentials.

    Parameters
    ----------
    url : str
        The URL to fix.

    Returns
    -------
    fixed_url : str
        The fixed URL.
    """
    try:
        # More flexible pattern that accepts any scheme format
        # Captures: anything://username:password@host_and_rest
        pattern = r"^([^:]+://)([^:/?#]+):([^@]+)@(.+)$"
        match = re.match(pattern, url)

        if match:
            scheme, username, password, host_part = match.groups()
            # URL encode the username and password
            # safe='' means encode all special characters
            encoded_username = quote(username, safe="")
            encoded_password = quote(password, safe="")

            # Reconstruct the URL
            fixed_url = f"{scheme}{encoded_username}:{encoded_password}@{host_part}"

            # Extract scheme name for logging
            scheme_name = scheme.rstrip("://")  # noqa: B005
            print(f"Fixed {scheme_name!r} URL encoding for special characters")

            return fixed_url

        print("WARNING: No regex match found!")
        return url

    except Exception as e:
        print(f"Could not fix URL: {e}")
        return url


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
    C_FORCE_ROOT: int = 1  # Suppress root user warning
    CELERY_OPTIMIZATION: str = "fair"  # Optimize Celery performance

    @field_validator("RABBITMQ_PORT", "MYSQL_PORT", mode="before")
    @classmethod
    def parse_port_fields(cls, v: str | int) -> int:
        """Parses port fields to ensure they are integers."""
        if isinstance(v, str):
            try:
                return int(v.strip())
            except ValueError:
                raise ValueError(f"Invalid port value: {v}") from None

        if isinstance(v, int) and not (1 <= v <= 65535):
            raise ValueError(f"Port must be between 1 and 65535, got {v}")

        return v

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
        url: str = (
            f"amqp://{self.RABBITMQ_DEFAULT_USER}:{self.RABBITMQ_DEFAULT_PASS.get_secret_value()}"
            f"@{self.RABBITMQ_HOST}:{self.RABBITMQ_PORT}/?heartbeat={self.RABBITMQ_HEARTBEAT}"
        )
        return fix_url_credentials(url)

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
        url: str = (
            f"db+mysql+pymysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD.get_secret_value()}"
            f"@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DATABASE}?charset=utf8mb4"
        )
        
        return fix_url_credentials(url)

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

        url: str = (
            f"mysql+pymysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD.get_secret_value()}"
            f"@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DATABASE}"
        )
        return fix_url_credentials(url)


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
