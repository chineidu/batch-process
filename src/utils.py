import asyncio
import logging
import sqlite3
import time
from functools import wraps
from pathlib import Path
from typing import Any, Callable

import aiosqlite
import requests  # type: ignore

from config import app_config
from schemas import ModelOutput


def async_timer(func: Callable[..., Any]) -> Callable[..., Any]:
    """
    A decorator that measures and prints the execution time of an async function.

    Parameters
    ----------
    func : Callable
        The async function to be timed.

    Returns
    -------
    Callable
        A wrapped async function that prints execution time.
    """

    @wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        start_time: float = time.perf_counter()
        result = await func(*args, **kwargs)
        duration: float = time.perf_counter() - start_time
        return result

    return wrapper


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


def parse_data(data: str) -> dict[str, Any]:
    """
    Parse data from a dictionary and return a tuple of values.
    """
    return ModelOutput.model_validate_json(data).model_dump(by_alias=True)


def init_database_sync() -> tuple[sqlite3.Connection, sqlite3.Cursor]:
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
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS failed_predictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            person_id TEXT NOT NULL,
            sex TEXT,
            age INTEGER,
            pclass INTEGER,
            sibsp INTEGER,
            parch INTEGER,
            fare REAL,
            embarked TEXT,
            survived INTEGER
        )
    """
    )
    conn.commit()

    return conn, cursor


async def init_database_async() -> aiosqlite.Connection:
    """
    Initialize SQLite database connection and create users table asynchronously.

    Returns
    -------
    aiosqlite.Connection
        The database connection object.
    """
    # Create the database file if it doesn't exist
    create_path(app_config.db.database)

    # Connect to the SQLite database (or create it if it doesn't exist)
    conn = await aiosqlite.connect(app_config.db.database)

    # Create a table
    await conn.execute(
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

    await conn.execute(
        """
        CREATE TABLE IF NOT EXISTS failed_predictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            person_id TEXT NOT NULL,
            sex TEXT,
            age INTEGER,
            pclass INTEGER,
            sibsp INTEGER,
            parch INTEGER,
            fare REAL,
            embarked TEXT,
            survived INTEGER
        )
    """
    )

    # Commit the changes
    await conn.commit()

    return conn


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


async def insert_data_async(conn: aiosqlite.Connection, data: str, logger: logging.Logger) -> None:
    """
    Insert data asynchronously into a table using a database connection.

    Parameters
    ----------
    conn : aiosqlite.Connection
        Asynchronous SQLite database connection object
    data : str
        JSON string containing prediction data
    logger : logging.Logger
        Logger instance for error reporting

    Returns
    -------
    None

    Raises
    ------
    aiosqlite.Error
        If a database-related error occurs during insertion
    Exception
        If any other unexpected error occurs
    """
    try:
        await _insert_data_async(conn, data=data)
    except aiosqlite.Error as e:
        logger.error(f"Database error when inserting data: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error when inserting data: {e}")
        raise


async def insert_dlq_data_async(
    conn: aiosqlite.Connection, data: str, logger: logging.Logger
) -> None:
    """
    Insert data asynchronously into a table using a database connection.
    """
    query: str = """
        INSERT INTO failed_predictions (person_id, sex, age, pclass, sibsp,
        parch, fare, embarked, survived)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    try:
        conn.execute(query, data)
    except aiosqlite.Error as e:
        logger.error(f"Database error when inserting data: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error when inserting data: {e}")
        raise


def download_file_from_gdrive(file_id: str, destination: str) -> None:
    download_url: str = f"https://drive.google.com//uc?export=download&id={file_id}"
    response = requests.get(download_url, stream=True)
    # Raise an exception for bad status codes
    response.raise_for_status()

    with open(destination, "wb") as file:
        for chunk in response.iter_content(chunk_size=8192):
            file.write(chunk)


async def download_file_from_gdrive_async(file_id: str, destination: str) -> None:
    return await asyncio.to_thread(download_file_from_gdrive, file_id, destination)
