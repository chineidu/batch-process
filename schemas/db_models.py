from contextlib import contextmanager
from datetime import datetime
from typing import Any, Generator, Optional

from sqlalchemy import JSON, String, Text, create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from config import app_config
from schemas import ModelOutput

engine: Engine = create_engine(app_config.db.db_path, echo=False)


class Base(DeclarativeBase):
    pass


class NERData(Base):
    """Data model for storing Named Entity Recognition (NER) data."""

    __tablename__: str = "ner_data"
    id: Mapped[int] = mapped_column(primary_key=True)
    status: Mapped[str] = mapped_column(String(50))
    data: Mapped[dict[str, Any]] = mapped_column(JSON)
    timestamp: Mapped[Optional[str]] = mapped_column("timestamp", default=datetime.now)
    created_at: Mapped[Optional[str]] = mapped_column("createdAt", default=datetime.now)

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


class TaskResult(Base):
    """Data model for storing task results."""

    __tablename__: str = "task_results"
    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    task_name: Mapped[str] = mapped_column(String(50), index=True)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    result: Mapped[dict[str, Any]] = mapped_column(JSON)
    error_message: Mapped[str] = mapped_column(Text)
    created_at: Mapped[Optional[str]] = mapped_column("createdAt", default=datetime.now)
    completed_at: Mapped[Optional[str]] = mapped_column("completedAt", default=datetime.now)

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


class EmailLog(Base):
    """Data model for storing email logs."""

    __tablename__: str = "email_logs"
    id: Mapped[int] = mapped_column(primary_key=True)
    recipient: Mapped[str] = mapped_column(String(50), index=True)
    subject: Mapped[str] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(20), default="pending")
    sent_at: Mapped[Optional[str]] = mapped_column("sentAt", default=datetime.now)
    created_at: Mapped[Optional[str]] = mapped_column("createdAt", default=datetime.now)

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


def add_record_to_db(data: ModelOutput | dict[str, Any]) -> dict[str, Any]:
    """
    Add a new NER record to the database.

    Parameters
    ----------
    db : Session
        SQLAlchemy database session.
    data : ModelOutput | dict[str, Any]
        Entity schema data containing NER information.

    Returns
    -------
    dict[str, Any]:
        The newly created and persisted NER record.
    """
    if not isinstance(data, ModelOutput):
        data = ModelOutput(**data)
    with get_db_session() as db:
        record: NERData = NERData(**data.model_dump())
        db.add(record)
        db.flush()

        return {
            "id": record.id,
            "status": record.status,
            "data": record.data,
            "timestamp": record.timestamp,
            "created_at": record.created_at,
        }

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
