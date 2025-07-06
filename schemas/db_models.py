from contextlib import contextmanager
from datetime import datetime
from typing import Any, Generator, Type, TypeVar

from pydantic import BaseModel
from sqlalchemy import JSON, String, Text, create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from config import app_config
from schemas import ModelOutput

engine: Engine = create_engine(app_config.db.db_path, echo=False)
T = TypeVar("T", bound="BaseModel")
D = TypeVar("D", bound="Base")


class Base(DeclarativeBase):
    pass


class NERData(Base):
    """Data model for storing Named Entity Recognition (NER) data."""

    __tablename__: str = "ner_data"
    id: Mapped[int] = mapped_column(primary_key=True)
    status: Mapped[str] = mapped_column(String(50))
    data: Mapped[dict[str, Any]] = mapped_column(JSON)
    timestamp: Mapped[str | None] = mapped_column("timestamp", default=datetime.now)
    created_at: Mapped[str | None] = mapped_column("createdAt", default=datetime.now)

    def __repr__(self) -> str:
        """
        Returns a string representation of the NERData object.

        Returns
        -------
        str
        """
        return (
            f"{self.__class__.__name__}(id={self.id!r}, status={self.status!r}, data={self.data!r})"
        )

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
    task_id: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    task_name: Mapped[str] = mapped_column(String(50), index=True)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    result: Mapped[dict[str, Any]] = mapped_column(JSON)
    error_message: Mapped[str] = mapped_column(Text)
    created_at: Mapped[str | None] = mapped_column("createdAt", default=datetime.now)
    completed_at: Mapped[str | None] = mapped_column("completedAt", default=datetime.now)

    def __repr__(self) -> str:
        """
        Returns a string representation of the NERData object.

        Returns
        -------
        str
        """
        return (
            f"{self.__class__.__name__}(task_id={self.task_id!r}, task_name={self.task_name!r}, "
            f"status={self.status!r})"
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
    status: Mapped[str] = mapped_column(String(20), default="pending")
    sent_at: Mapped[str | None] = mapped_column("sentAt", default=datetime.now)
    created_at: Mapped[str | None] = mapped_column("createdAt", default=datetime.now)

    def __repr__(self) -> str:
        """
        Returns a string representation of the email log.

        Returns
        -------
        str
        """
        return (
            f"{self.__class__.__name__}(recipient={self.recipient!r}, subject={self.subject!r}, "
            f"status={self.status!r})"
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


def bulk_insert_records(data_list: list[ModelOutput] | list[dict[str, Any]]) -> None:
    """
    High-performance bulk insert using SQLAlchemy Core.

    Parameters
    ----------
    data_list : list[ModelOutput] | list[dict[str, Any]]
        List of EntitySchemaResponse objects or dictionaries containing data to be inserted.

    Returns
    -------
    None
        This function performs database operations without returning any value.

    Raises
    ------
    Exception
        Any database-related exception that occurs during bulk insert operation.
    """
    if not data_list:
        return

    if not isinstance(data_list[0], ModelOutput):
        data_list = [ModelOutput(**data) for data in data_list]  # type: ignore

    records_data: list[dict[str, Any]] = [data.model_dump() for data in data_list]  # type: ignore

    with get_db_session() as db:
        db.bulk_insert_mappings(NERData, records_data)  # type: ignore


def init_db() -> None:
    """
    Initialize the database connection and create all tables.

    Returns
    -------
    None
    """
    # Creates tables
    Base.metadata.create_all(engine)
