import sqlite3
from pathlib import Path
from typing import Any

import aiosqlite

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


def insert_data_sync(conn: sqlite3.Connection, *, cursor: sqlite3.Cursor, data: str) -> None:
    """
    Insert data synchronously into the predictions table.

    Parameters
    ----------
    conn : sqlite3.Connection
        SQLite database connection object
    cursor : sqlite3.Cursor
        SQLite cursor object
    data : str
        JSON string containing prediction data

    Returns
    -------
    None
    """
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


async def _insert_data_async(conn: aiosqlite.Connection, data: str) -> None:
    """
    Internal helper function to insert data asynchronously into the predictions table.

    Parameters
    ----------
    conn : aiosqlite.Connection
        Asynchronous SQLite database connection object
    data : str
        JSON string containing prediction data

    Returns
    -------
    None
    """
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

    await conn.execute(query, record)
    await conn.commit()


async def insert_data_async(data: str) -> None:
    """
    Insert data asynchronously into the predictions table using a database connection.

    Parameters
    ----------
    data : str
        JSON string containing prediction data

    Returns
    -------
    None
    """
    # Create the database file if it doesn't exist
    create_path(app_config.db.database)

    async with aiosqlite.connect(app_config.db.database) as conn:
        await _insert_data_async(conn, data=data)
