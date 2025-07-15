from contextlib import contextmanager
from datetime import datetime
from typing import Any, Generator, TypeVar

from pydantic import BaseModel
from sqlalchemy import (
    JSON,
    DateTime,
    Float,
    Integer,
    LargeBinary,
    String,
    Text,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column
from sqlalchemy.orm.properties import MappedColumn

from celery.signals import worker_process_init
from config import app_config
from config.settings import refresh_settings
from src import create_logger

from .utilities import DatabasePool

logger = create_logger(name="database_utilities")
settings = refresh_settings()
T = TypeVar("T", bound="BaseModel")
D = TypeVar("D", bound="Base")


class Base(DeclarativeBase):
    """Base class for all database models."""

    pass


# Global pool instance
_db_pool: DatabasePool | None = None


def get_db_pool() -> DatabasePool:
    """Get or create the global database pool."""
    global _db_pool
    if _db_pool is None:
        if settings.ENVIRONMENT == "test":
            DATABASE_URL: str = app_config.db.db_path
        elif settings.ENVIRONMENT in ["dev", "prod"]:
            DATABASE_URL = (
                f"postgresql+psycopg2://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD.get_secret_value()}"
                f"@localhost:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"
            )
        logger.info(f"Connected to {settings.ENVIRONMENT!r} environment database.")
        _db_pool = DatabasePool(DATABASE_URL)
    return _db_pool


@worker_process_init.connect
def init_worker(**kwargs) -> None:
    """Disposes of the database engine when a new worker process starts necessary for
    cleaning up connections and freeing resources.
    """

    db_pool = get_db_pool()
    db_pool.engine.dispose()


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """Get a database session.

    Yields
    ------
    Session
        A database session
    """
    db_pool = get_db_pool()
    with db_pool.get_session() as session:
        yield session


def init_db() -> None:
    """This function is used to create the tables in the database.
    It should be called once when the application starts."""
    db_pool = get_db_pool()
    # Create all tables in the database
    Base.metadata.create_all(db_pool.engine)
    logger.info("Database initialized")


# ===== Database Models =====


class NERResult(Base):
    """Data model for storing Named Entity Recognition (NER) data."""

    __tablename__: str = "ner_results"
    id: Mapped[int] = mapped_column(primary_key=True)
    status: Mapped[str] = mapped_column(String(50))
    data: Mapped[dict[str, Any]] = mapped_column(JSON)
    timestamp: Mapped[str | None] = mapped_column(DateTime(timezone=True), default=func.now())
    created_at: Mapped[str | None] = mapped_column("createdAt", DateTime(timezone=True), default=func.now())

    def __repr__(self) -> str:
        """
        Returns a string representation of the NERData object.

        Returns
        -------
        str
        """
        return f"{self.__class__.__name__}(id={self.id!r}, status={self.status!r}, data={self.data!r})"


class TaskResult(Base):
    """Data model for storing task results."""

    __tablename__: str = "task_results"
    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[str] = mapped_column("taskId", String(50), unique=True, index=True)
    task_name: Mapped[str] = mapped_column("taskName", String(50), index=True)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    result: Mapped[dict[str, Any]] = mapped_column(JSON)
    error_message: Mapped[str] = mapped_column("errorMessage", Text)
    created_at: Mapped[str | None] = mapped_column("createdAt", DateTime(timezone=True), default=func.now())
    completed_at: Mapped[datetime] = mapped_column("completedAt", DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:
        """
        Returns a string representation of the NERData object.

        Returns
        -------
        str
        """
        return (
            f"{self.__class__.__name__}(task_id={self.task_id!r}, task_name={self.task_name!r}, status={self.status!r})"
        )


class EmailLog(Base):
    """Data model for storing email logs."""

    __tablename__: str = "email_logs"
    id: Mapped[int] = mapped_column(primary_key=True)
    recipient: Mapped[str] = mapped_column(String(50), index=True)
    subject: Mapped[str] = mapped_column(String(100))
    body: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    created_at: Mapped[datetime | None] = mapped_column("createdAt", DateTime(timezone=True), default=func.now())
    sent_at: Mapped[datetime] = mapped_column("sentAt", DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:
        """
        Returns a string representation of the email log.

        Returns
        -------
        str
        """
        return (
            f"{self.__class__.__name__}(recipient={self.recipient!r}, subject={self.subject!r}, status={self.status!r})"
        )


class DataProcessingJob(Base):
    """Data model for storing email logs."""

    __tablename__: str = "data_processing_jobs"
    id: Mapped[int] = mapped_column(primary_key=True)
    job_name: Mapped[str] = mapped_column("jobName", String(50), index=True)
    input_data: Mapped[str] = mapped_column("inputData", Text)
    output_data: Mapped[str] = mapped_column("outputData", Text)
    processing_time: Mapped[float] = mapped_column("processingTime", Float)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    created_at: Mapped[datetime | None] = mapped_column("createdAt", DateTime(timezone=True), default=func.now())
    completed_at: Mapped[datetime] = mapped_column("completedAt", DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:
        """
        Returns a string representation of the email log.

        Returns
        -------
        str
        """
        return (
            f"{self.__class__.__name__}(job_name={self.job_name!r}, created_at={self.created_at!r}, "
            f"status={self.status!r})"
        )


# Celery specific
class CeleryTaskMeta(Base):
    """Data model for storing Celery task meta."""

    __tablename__: str = "celery_task_meta"
    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[str] = mapped_column("taskId", String(255), unique=True, index=True)
    status: Mapped[str] = mapped_column(String(50), default="PENDING")
    result: MappedColumn[Any] = mapped_column(LargeBinary)
    date_done: Mapped[str] = mapped_column("dateDone", DateTime(timezone=True), nullable=True)
    traceback: Mapped[str] = mapped_column(String)
    name: Mapped[str] = mapped_column(String(255))
    args: MappedColumn[Any] = mapped_column(LargeBinary)
    kwargs: MappedColumn[Any] = mapped_column(LargeBinary)
    worker: Mapped[str] = mapped_column(String(255))
    retries: Mapped[int] = mapped_column(Integer, default=0)
    queue: Mapped[str] = mapped_column(String(255))

    def __repr__(self) -> str:
        """
        Returns a string representation of the email log.

        Returns
        -------
        str
        """
        return (
            f"{self.__class__.__name__}(task_id={self.task_id!r}, date_done={self.date_done!r} status={self.status!r})"
        )
