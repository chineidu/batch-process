from contextlib import contextmanager
from datetime import datetime
from typing import Any, Generator, Type, TypeVar

from pydantic import BaseModel
from sqlalchemy import JSON, Float, Integer, LargeBinary, String, Text, create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column
from sqlalchemy.orm.properties import MappedColumn

from config import app_config
from config.settings import refresh_settings

settings = refresh_settings()

if settings.ENVIRONMENT == "test":
    DATABASE_URL: str = app_config.db.db_path
elif settings.ENVIRONMENT in ["dev", "prod"]:
    DATABASE_URL = (
        f"postgresql+psycopg2://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD.get_secret_value()}"
        f"@localhost:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"
    )
print(f"Connected to {settings.ENVIRONMENT!r} environment database.")

engine: Engine = create_engine(DATABASE_URL, echo=False)
T = TypeVar("T", bound="BaseModel")
D = TypeVar("D", bound="Base")


class Base(DeclarativeBase):
    pass


class NERResult(Base):
    """Data model for storing Named Entity Recognition (NER) data."""

    __tablename__: str = "ner_results"
    id: Mapped[int] = mapped_column(primary_key=True)
    status: Mapped[str] = mapped_column(String(50))
    data: Mapped[dict[str, Any]] = mapped_column(JSON)
    timestamp: Mapped[str | None] = mapped_column(default=datetime.now)
    created_at: Mapped[str | None] = mapped_column("createdAt", default=datetime.now)

    def __repr__(self) -> str:
        """
        Returns a string representation of the NERData object.

        Returns
        -------
        str
        """
        return f"{self.__class__.__name__}(id={self.id!r}, status={self.status!r}, data={self.data!r})"

    def output_fields(self) -> list[str]:
        """Get the output fields."""
        return [
            "id",
            "status",
            "data",
            "timestamp",
            "created_at",
        ]


class TaskResult(Base):
    """Data model for storing task results."""

    __tablename__: str = "task_results"
    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[str] = mapped_column("taskId", String(50), unique=True, index=True)
    task_name: Mapped[str] = mapped_column("taskName", String(50), index=True)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    result: Mapped[dict[str, Any]] = mapped_column(JSON)
    error_message: Mapped[str] = mapped_column("errorMessage", Text)
    created_at: Mapped[str | None] = mapped_column("createdAt", default=datetime.now)
    completed_at: Mapped[datetime] = mapped_column("completedAt", nullable=True)

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

    def output_fields(self) -> list[str]:
        """Get the output fields."""
        return [
            "id",
            "task_id",
            "task_name",
            "status",
            "result",
            "error_message",
            "created_at",
            "completed_at",
        ]


class EmailLog(Base):
    """Data model for storing email logs."""

    __tablename__: str = "email_logs"
    id: Mapped[int] = mapped_column(primary_key=True)
    recipient: Mapped[str] = mapped_column(String(50), index=True)
    subject: Mapped[str] = mapped_column(String(100))
    body: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    created_at: Mapped[datetime | None] = mapped_column("createdAt", default=datetime.now)
    sent_at: Mapped[datetime] = mapped_column("sentAt", nullable=True)

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

    def output_fields(self) -> list[str]:
        """Get the output fields."""
        return [
            "id",
            "recipient",
            "subject",
            "status",
            "sent_at",
            "created_at",
        ]


class DataProcessingJob(Base):
    """Data model for storing email logs."""

    __tablename__: str = "data_processing_jobs"
    id: Mapped[int] = mapped_column(primary_key=True)
    job_name: Mapped[str] = mapped_column("jobName", String(50), index=True)
    input_data: Mapped[str] = mapped_column("inputData", Text)
    output_data: Mapped[str] = mapped_column("outputData", Text)
    processing_time: Mapped[float] = mapped_column("processingTime", Float)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    created_at: Mapped[datetime | None] = mapped_column("createdAt", default=datetime.now)
    completed_at: Mapped[datetime] = mapped_column("completedAt", nullable=True)

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

    def output_fields(self) -> list[str]:
        """Get the output fields."""
        return [
            "id",
            "job_name",
            "input_data",
            "output_data",
            "processing_time",
            "status",
            "created_at",
            "completed_at",
        ]


# Celery specific
class CeleryTaskMeta(Base):
    """Data model for storing Celery task meta."""

    __tablename__: str = "celery_task_meta"
    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[str] = mapped_column("taskId", String(255), unique=True, index=True)
    status: Mapped[str] = mapped_column(String(50), default="PENDING")
    result: MappedColumn[Any] = mapped_column(LargeBinary)
    date_done: Mapped[str] = mapped_column("dateDone", nullable=True)
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

    def output_fields(self) -> list[str]:
        """Get the output fields."""
        return [
            "id",
            "task_id",
            "status",
            "result",
            "date_done",
            "traceback",
            "name",
            "args",
            "kwargs",
            "worker",
            "retries",
            "queue",
        ]


class CeleryTasksetMeta(Base):
    """Data model for storing email logs."""

    __tablename__: str = "celery_taskset_meta"
    id: Mapped[int] = mapped_column(primary_key=True)
    task_set_id: Mapped[str] = mapped_column("taskSetId", String(255), unique=True, index=True)
    result: MappedColumn[Any] = mapped_column(LargeBinary)
    date_done: Mapped[str] = mapped_column("dateDone", nullable=True)

    def __repr__(self) -> str:
        """
        Returns a string representation of the email log.

        Returns
        -------
        str
        """
        return f"{self.__class__.__name__}(task_set_id={self.task_set_id!r}, date_done={self.date_done!r})"

    def output_fields(self) -> list[str]:
        """Get the output fields."""
        return [
            "id",
            "task_set_id",
            "result",
            "date_done",
        ]


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """
    Creates and manages a database session using a context manager.

    This function creates a new database session, yields it for use,
    and handles commit/rollback operations automatically. The session
    is properly closed after use, even if an exception occurs.

    Yields
    ------
    Session
        An active SQLAlchemy database session.

    Raises
    ------
    Exception
        Any exception that occurs during database operations.
    """
    session: Session = Session(engine)
    try:
        yield session
        session.commit()

    except Exception:
        session.rollback()
        raise

    finally:
        session.close()


def add_record_to_db(data: dict[str, Any], schema: Type[T], data_model: Type[D]) -> dict[str, Any]:
    """
    Add a record to the database using the provided data, schema, and data model.

    Parameters
    ----------
    data : dict[str, Any]
        Dictionary containing the data to be added to the database.
    schema : Type[T]
        Type of the schema class used for data validation and transformation.
    data_model : Type[D]
        Type of the database model class where the record will be stored.

    Returns
    -------
    dict[str, Any]
        Dictionary containing the record's fields after being added to the database.
        Returns an empty dictionary if the operation fails.

    """
    if isinstance(data, dict):
        data_dict: dict[str, Any] = schema(**data).to_data_model_dict()  # type: ignore
    with get_db_session() as db:
        record = data_model(**data_dict)
        db.add(record)
        db.flush()

        return {key: getattr(record, key) for key in record.output_fields()}  # type: ignore

    return {}


def bulk_insert_records(data: list[dict[str, Any]], schema: Type[T], data_model: Type[D]) -> None:
    """
    Bulk insert multiple records into the database using the provided data, schema, and data model.

    Parameters
    ----------
    data : list[dict[str, Any]]
        List of dictionaries containing the data to be added to the database.
    schema : Type[T]
        Type of the schema class used for data validation and transformation.
    data_model : Type[D]
        Type of the database model class where the records will be stored.

    Returns
    -------
    None
    """
    if isinstance(data, list):
        data_list: list[dict[str, Any]] = [schema(**row).to_data_model_dict() for row in data]  # type: ignore

    with get_db_session() as db:
        db.bulk_insert_mappings(data_model, data_list)  # type: ignore


def init_db() -> None:
    """
    Initialize the database connection and create all tables.

    Returns
    -------
    None
    """
    # Creates tables
    Base.metadata.create_all(engine)
