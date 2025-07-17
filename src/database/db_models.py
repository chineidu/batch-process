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
from schemas import CeleryTasksLogSchema
from src import create_logger
from src.celery import BaseCustomTask, BaseMLTask

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
            DATABASE_URL = settings.database_url
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
class PersonLog(Base):
    """Data model for storing person data."""

    __tablename__: str = "persons"
    id: Mapped[int] = mapped_column(primary_key=True)
    person_id: Mapped[str] = mapped_column("personId", String(50), unique=True, index=True)
    sex: Mapped[str] = mapped_column(String(8))
    age: Mapped[float] = mapped_column(Float)
    pclass: Mapped[int] = mapped_column(Integer)
    sibsp: Mapped[int] = mapped_column(Integer)
    parch: Mapped[int] = mapped_column(Integer)
    fare: Mapped[float] = mapped_column(Float)
    embarked: Mapped[str] = mapped_column(String(8))
    survived: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[str | None] = mapped_column("createdAt", DateTime(timezone=True), default=func.now())

    def __repr__(self) -> str:
        """
        Returns a string representation of the NERData object.

        Returns
        -------
        str
        """
        return (
            f"{self.__class__.__name__}(person_id={self.person_id!r}, sex={self.sex!r}, created_at={self.created_at!r})"
        )


class PredictionLog(Base):
    """Data model for storing prediction data."""

    __tablename__: str = "predictions"
    id: Mapped[int] = mapped_column(primary_key=True)
    data: Mapped[dict[str, Any]] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(10))
    created_at: Mapped[str | None] = mapped_column("createdAt", DateTime(timezone=True), default=func.now())

    def __repr__(self) -> str:
        """
        Returns a string representation of the NERData object.

        Returns
        -------
        str
        """
        return f"{self.__class__.__name__}(data={self.data!r}, status={self.status!r}, created_at={self.created_at!r})"


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


class PredictionProcessingJobLog(Base):
    """Data model for storing email logs."""

    __tablename__: str = "prediction_processing_jobs"
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


class DataProcessingJobLog(Base):
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


class CeleryTasksLog(Base):
    """Data model for storing Celery task meta."""

    __tablename__: str = "celery_tasks_log"
    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[str] = mapped_column("taskId", String(255), unique=True, index=True)
    task_name: Mapped[str] = mapped_column("taskName", String(255), index=True)
    status: Mapped[str] = mapped_column(String(50), default="PENDING")
    updated_at: Mapped[datetime | None] = mapped_column("updatedAt", DateTime(timezone=True), nullable=True)
    args: MappedColumn[Any] = mapped_column(Text, nullable=True)
    kwargs: MappedColumn[Any] = mapped_column(Text, nullable=True)
    result: MappedColumn[Any] = mapped_column(Text, nullable=True)
    error: Mapped[str] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        """
        Returns a string representation of the email log.

        Returns
        -------
        str
        """
        return f"{self.__class__.__name__}(task_id={self.task_id!r}, updated_at={self.updated_at!r} status={self.status!r})"


# ===== Mixins =====
class DatabaseLoggingMixin:
    def _save_log(self, task_id: str, status: str, **extra_data: dict[str, Any]) -> None:
        """Saves a log entry for a Celery task in the database.

        Parameters
        ----------
        task_id : str
            The ID of the task.
        status : str
            The status of the task.
        **extra_data : dict[str, Any]
            Additional data to store in the log entry.

        Notes
        -----
        Exceptions are caught and logged, and the method does not re-raise any exceptions.
        """
        try:
            with get_db_session() as session:
                statement = session.query(CeleryTasksLog).where(CeleryTasksLog.task_id == task_id)
                existing_log = session.execute(statement).scalar_one_or_none()
                if existing_log:
                    # Update log
                    existing_log.status = status
                    existing_log.updated_at = datetime.now()
                    for key, value in extra_data.items():
                        setattr(existing_log, key, value)
                else:
                    # Create new log
                    _data = {
                        "task_id": task_id,
                        "status": status,
                        "updated_at": datetime.now(),
                    } | extra_data
                    data = CeleryTasksLogSchema(**_data).model_dump()  # type: ignore
                    new_log = CeleryTasksLog(**data)
                    session.add(new_log)
                    session.flush()
        except Exception as e:
            logger.error(f"Failed to save log: {e}")

    def on_success(self, retval: Any, task_id: str, args: Any, kwargs: Any) -> None:
        """Saves the task exception and keyword arguments to the database on success.

        Parameters
        ----------
        retval : Any
            The return value of the task.
        task_id : str
            The unique ID of the task.
        args : Any
            The positional arguments passed to the task.
        kwargs : Any
            The keyword arguments passed to the task.

        Returns
        -------
        None
            This method does not return any value.

        Notes
        -----
        This method overrides the `on_success` method from the parent class
        and ensures that the parent's `on_success` is called if it exists.
        The signature must match the parent's `on_success` method.
        """
        retval = str(retval)[:1_000]  # Truncate long results
        task_name = self.name  # type: ignore
        self._save_log(task_id, task_name=task_name, status="SUCCESS", result=retval, args=args, kwargs=kwargs)
        # Call paret's on_success method if it exists
        if hasattr(super(), "on_success"):
            super().on_success(retval, task_id, args, kwargs)  # type: ignore

    def on_failure(self, exc: Any, task_id: str, args: Any, kwargs: Any, einfo: Any) -> None:
        """Saves the task exception and keyword arguments to the database on failure.

        Parameters
        ----------
        exc : Any
            The exception that was raised by the task.
        task_id : str
            The unique ID of the task.
        args : Any
            The positional arguments passed to the task.
        kwargs : Any
            The keyword arguments passed to the task.
        einfo : Any
            Exception information, including traceback.

        Returns
        -------
        None
            This method does not return any value.

        Notes
        -----
        This method overrides the `on_failure` method from the parent class
        and ensures that the parent's `on_failure` is called if it exists.
        The signature must match the parent's `on_failure` method.
        """
        einfo = str(einfo)[:1_000]  # Truncate long results
        task_name = self.name  # type: ignore
        self._save_log(task_id, task_name=task_name, status="FAILURE", args=args, kwargs=kwargs, error=einfo)
        # Call paret's on_failure method if it exists
        if hasattr(super(), "on_failure"):
            super().on_failure(exc, task_id, args, kwargs, einfo)  # type: ignore

    def on_retry(self, exc: Any, task_id: str, args: Any, kwargs: Any, einfo: Any) -> None:
        """Saves the task exception and keyword arguments to the database on retry.

        Parameters
        ----------
        exc : Any
            The exception that was raised by the task.
        task_id : str
            The unique ID of the task.
        args : Any
            The positional arguments passed to the task.
        kwargs : Any
            The keyword arguments passed to the task.
        einfo : Any
            Exception information, including traceback.

        Returns
        -------
        None
            This method does not return any value.

        Notes
        -----
        This method overrides the `on_retry` method from the parent class
        and ensures that the parent's `on_retry` is called if it exists.
        The signature must match the parent's `on_retry` method.
        """
        einfo = str(einfo)[:1_000]  # Truncate long results
        task_name = self.name  # type: ignore
        self._save_log(task_id, task_name=task_name, status="RETRY", args=args, kwargs=kwargs, error=einfo)
        # Call paret's on_retry method if it exists
        if hasattr(super(), "on_retry"):
            super().on_retry(exc, task_id, args, kwargs, einfo)  # type: ignore


class BaseTask(DatabaseLoggingMixin, BaseCustomTask):
    """Base class for tasks with database logging capabilities.
    Adds on_success, on_failure, and on_retry methods that save the task log to the database.
    """

    pass


class MLTask(DatabaseLoggingMixin, BaseMLTask, BaseCustomTask):
    """Base class for machine learning tasks with database logging capabilities.
    Adds on_success, on_failure, and on_retry methods that save the task log to the database.
    """

    pass
