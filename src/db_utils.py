import sqlite3
from pathlib import Path
from typing import Any

from config import app_config
from schemas import ModelOutput


def create_path(path: str | Path) -> None:
    """
    Create parent directories for the given path if they don't exist.

    Parameters
    ----------
    path : str | Path
        The file path for which to create parent directories.

    Returns
    -------
    None
    """
    Path(path).parent.mkdir(parents=True, exist_ok=True)


def init_database() -> tuple[sqlite3.Connection, sqlite3.Cursor]:
    """
    Initialize SQLite database connection and create users table.

    Returns
    -------
    tuple[sqlite3.Connection, sqlite3.Cursor]
        A tuple containing the database connection and cursor objects.
    """
    # Create the database file if it doesn't exist
    create_path(app_config.db.database)

    # Connect to the SQLite database (or create it if it doesn't exist)
    conn = sqlite3.connect(app_config.db.database)

    # Create a cursor object to execute SQL commands
    cursor = conn.cursor()

    # Create a table
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS predictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            status TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            user_id TEXT NOT NULL,
            survived INTEGER,
            probability REAL
        )
    """
    )

    return conn, cursor


def parse_data(data: str) -> dict[str, Any]:
    """
    Parse data from a dictionary and return a tuple of values.
    """
    return ModelOutput.model_validate_json(data).model_dump(by_alias=True)


def insert_data(conn: sqlite3.Connection, *, cursor: sqlite3.Cursor, data: str) -> None:
    parsed_data: dict[str, Any] = parse_data(data)
    query: str = """
        INSERT INTO predictions (status, timestamp, user_id, survived, probability)
        VALUES (?, ?, ?, ?, ?)
    """
    record: tuple[str, ...] = (
        parsed_data["status"],
        parsed_data["timestamp"],
        parsed_data["data"]["id"],
        parsed_data["data"]["survived"],
        parsed_data["data"]["probability"],
    )

    cursor.execute(query, record)
    conn.commit()
