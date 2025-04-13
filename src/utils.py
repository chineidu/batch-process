import asyncio
import logging
import sqlite3
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncGenerator

import aiosqlite
import requests  # type: ignore

from config import app_config
from schemas import ModelOutput, MultiPersonsSchema, PersonSchema
from src import create_logger

logger = create_logger(name="db_utils")

# Queries
QUERY: str = """
        INSERT INTO predictions (status, timestamp, user_id, survived, probability)
        VALUES (?, ?, ?, ?, ?)
    """
DLQ_QUERY: str = """
        INSERT INTO failed_predictions (person_id, sex, age, pclass,
        sibsp, parch, fare, embarked, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """


def create_path(path: str | Path) -> None:
    """
    Create parent directories for the given path if they don't exist.

    Parameters
    ----------
    path : str | Path
        The file path for which to create parent directories.

    """
    Path(path).parent.mkdir(parents=True, exist_ok=True)


def parse_data(data: str | ModelOutput) -> tuple[Any, ...]:
    """
    Parse data from a dictionary and return a tuple of values.

    Parameters
    ----------
    data : str | ModelOutput
        The input data to be parsed.

    Returns
    -------
    tuple[Any, ...]
        A tuple containing the parsed values.

    Raises
    ------
    ValueError
        If the input data is not a dictionary.
    """
    if not isinstance(data, (str, ModelOutput)):
        raise ValueError("Invalid data type. Expected str or ModelOutput.")

    if isinstance(data, str):
        formated_data: dict[str, Any] = ModelOutput.model_validate_json(data).model_dump(
            by_alias=True
        )
    elif isinstance(data, ModelOutput):
        formated_data = data.model_dump(by_alias=True)

    formated_data: tuple[str, ...] = (  # type: ignore
        formated_data["status"],
        formated_data["timestamp"],
        formated_data["data"]["id"],
        formated_data["data"]["survived"],
        formated_data["data"]["probability"],
    )
    return formated_data  # type: ignore


def _extract_dlq_data(data: dict[str, Any]) -> tuple[Any, ...]:
    """
    Extract data from a dictionary and return a tuple of values.

    Parameters
    ----------
    data : dict[str, Any]
        The input data to be extracted.

    Returns
    -------
    tuple[Any, ...]
        A tuple containing the extracted values.
    """
    result: tuple[str, ...] = (
        data["id"],
        data["sex"],
        data["age"],
        data["pclass"],
        data["sibsp"],
        data["parch"],
        data["fare"],
        data["embarked"],
        data["timestamp"],
    )

    return result


class DatabaseConnectionPool:
    """
    A singleton class that manages a pool of database connections asynchronously.

    This class implements a connection pool pattern to efficiently manage and reuse
    database connections. It uses asyncio.Lock to prevent race conditions by ensuring
    only one coroutine can access shared resources at a time.
    """

    _instance: "DatabaseConnectionPool | None" = None
    _is_initialized: bool | None = None

    def __new__(cls) -> "DatabaseConnectionPool":
        """
        Create or return the singleton instance of DatabaseConnectionPool.

        Returns
        -------
        DatabaseConnectionPool
            The singleton instance
        """
        if cls._instance is None:
            cls._instance = super().__new__(cls)

        return cls._instance

    def __init__(self) -> None:
        """
        Initialize the connection pool if not already initialized.

        Creates the initial pool of connections and sets up required attributes.
        """
        if not self._is_initialized:
            self._active_connections: int = 0
            self._connection_pool: asyncio.Queue[aiosqlite.Connection] = asyncio.Queue()
            self._lock: asyncio.Lock = asyncio.Lock()
            self._is_initialized = True

            # Default values can be overriden by .configure()
            self._db_path = None
            self._max_connections: int = 5

    async def initialize(self) -> None:
        """
        Initialize the connection pool with the maximum number of connections.
        """
        async with self._lock:
            # If close all connections if any
            while not self._connection_pool.empty():
                await self.close()

            # Otherwise, create the connections
            for _ in range(self._max_connections):
                if self._db_path is not None:
                    create_path(self._db_path)
                    conn: aiosqlite.Connection = await aiosqlite.connect(self._db_path)
                    # Add durability settings
                    await conn.execute("PRAGMA journal_mode = WAL")
                    await conn.execute("PRAGMA synchronous = NORMAL")
                    await self._connection_pool.put(conn)

    def _configure(self, db_path: str | Path, max_connections: int = 5) -> None:
        self._db_path = db_path  # type: ignore
        self._max_connections = max_connections

    @classmethod
    async def create_pool(
        cls, db_path: str | Path | None = None, max_connections: int = 5
    ) -> "DatabaseConnectionPool":
        """
        Create a new instance of DatabaseConnectionPool.

        Parameters
        ----------
        db_path : str | Path | None, optional
            The path to the database file, by default None
        max_connections : int, optional
            The maximum number of connections to keep in the pool, by default 5

        Returns
        -------
        DatabaseConnectionPool
            A new instance of DatabaseConnectionPool

        Raises
        ------
        ValueError
            If the database connection pool has already been initialized.
        """
        instance = cls()

        if instance._db_path is not None:
            raise ValueError("Database connection pool has already been initialized. ")
        if instance._db_path is None:
            instance._configure(db_path, max_connections)  # type: ignore

        await instance.initialize()
        return instance

    async def acquire(self) -> aiosqlite.Connection:
        """
        Acquire a database connection from the pool.

        Returns
        -------
        aiosqlite.Connection
            A database connection

        Notes
        -----
        If the pool is empty and max connections haven't been reached,
        creates a new connection. Otherwise, waits for an available connection.
        """
        async with self._lock:
            if not self._connection_pool.empty():
                self._active_connections += 1
                return await self._connection_pool.get()

            if self._active_connections < self._max_connections:
                self._active_connections += 1
                return await aiosqlite.connect(self._db_path)  # type: ignore

            self._active_connections += 1
            return await self._connection_pool.get()

    async def release(self, conn: aiosqlite.Connection) -> None:
        """
        Release a connection back to the pool.

        Parameters
        ----------
        conn : aiosqlite.Connection
            The connection to be released
        """
        async with self._lock:
            self._active_connections -= 1

            if self._connection_pool.qsize() < self._max_connections:
                await self._connection_pool.put(conn)
            else:
                await conn.close()

    async def close(self) -> None:
        """
        Close all connections in the pool and reset the pool state.
        """
        async with self._lock:
            while not self._connection_pool.empty():
                conn = await self._connection_pool.get()
                await conn.close()
            self._active_connections = 0
            self._is_initialized = False

    @asynccontextmanager
    async def connection(self) -> AsyncGenerator[aiosqlite.Connection, None]:
        """
        Context manager for acquiring and releasing database connections.

        Yields
        ------
        aiosqlite.Connection
            A database connection from the pool

        Notes
        -----
        Automatically releases the connection when the context is exited.
        """
        conn = await self.acquire()
        try:
            yield conn
        except Exception as e:
            logger.error(f"Error during database operation: {e}")
            raise
        finally:
            await self.release(conn)


@asynccontextmanager
async def transaction(
    conn: aiosqlite.Connection,
) -> AsyncGenerator[aiosqlite.Connection, None]:
    """
    A context manager for managing database transactions with aiosqlite.

    Parameters
    ----------
    conn : aiosqlite.Connection
        The database connection

    Yields
    -------
    aiosqlite.Connection
        The database connection

    Raises
    ------
    Exception
        If an error occurs during the transaction
    """
    try:
        await conn.execute("BEGIN")
        yield conn
        await conn.commit()

    except Exception as e:
        await conn.rollback()
        raise e


def init_database_sync() -> tuple[sqlite3.Connection, sqlite3.Cursor]:
    """
    Initialize SQLite database connection and create users table.

    Returns
    -------
    tuple[sqlite3.Connection, sqlite3.Cursor]
        A tuple containing the database connection and cursor objects.
    """
    # Create the database file if it doesn't exist
    create_path(app_config.db.db_path)

    # Connect to the SQLite database (or create it if it doesn't exist)
    conn = sqlite3.connect(app_config.db.db_path)

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
            timestamp TEXT NOT NULL
        )
    """
    )
    conn.commit()

    return conn, cursor


async def init_database_async(pool: DatabaseConnectionPool) -> None:
    """
    Initialize SQLite database connection and create users table asynchronously.

    Parameters
    ----------
    pool : DatabaseConnectionPool
        The database connection pool
    """
    async with pool.connection() as conn:
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
                timestamp TEXT NOT NULL
            )
        """
        )

        # Commit the changes
        await conn.commit()


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

    """
    parsed_data: tuple[str, ...] = parse_data(data)
    cursor.execute(QUERY, parsed_data)

    conn.commit()


async def _insert_data_async(conn: aiosqlite.Connection, data: str | ModelOutput) -> None:
    """
    Internal helper function to insert data asynchronously into the predictions table.

    Parameters
    ----------
    conn : aiosqlite.Connection
        Asynchronous SQLite database connection object
    data : str | ModelOutput
        JSON string or ModelOutput object containing prediction data

    """
    parsed_data: tuple[str, ...] = parse_data(data)
    await conn.execute(QUERY, parsed_data)

    await conn.commit()


async def insert_data_async(
    pool: DatabaseConnectionPool, data: str | ModelOutput, logger: logging.Logger
) -> None:
    """
    Insert data asynchronously into a table using a database connection.

    Parameters
    ----------
    pool : DatabaseConnectionPool
        Database connection pool
    data : str | ModelOutput
        JSON string or ModelOutput object containing prediction data
    logger : logging.Logger
        Logger instance for error reporting

    Raises
    ------
    aiosqlite.Error
        If a database-related error occurs during insertion
    Exception
        If any other unexpected error occurs
    """
    try:
        async with pool.connection() as conn:
            async with transaction(conn):
                await _insert_data_async(conn, data=data)
    except aiosqlite.Error as e:
        logger.error(f"Database error when inserting data: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error when inserting data: {e}")
        raise


async def insert_dlq_data_async(
    pool: DatabaseConnectionPool, data: str, logger: logging.Logger
) -> None:
    """
    Insert data asynchronously into a table using a database connection.

    Parameters
    ----------
    pool : DatabaseConnectionPool
        Database connection pool
    data : str
        JSON string containing prediction data
    logger : logging.Logger
        Logger instance for error reporting

    Raises
    ------
        aiosqlite.Error: If there's an error connecting to the database
        Exception: If any other unexpected error occurs
    """

    try:
        async with pool.connection() as conn:
            async with transaction(conn):
                data: dict[str, Any] = PersonSchema.model_validate_json(data).model_dump()  # type: ignore
                result: tuple[str, ...] = _extract_dlq_data(data)  # type: ignore
                await conn.execute(DLQ_QUERY, result)
    except aiosqlite.Error as e:
        logger.error(f"Database error when inserting data: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error when inserting data: {e}")
        raise


async def insert_batch_dlq_data_async(
    pool: DatabaseConnectionPool, data: str | MultiPersonsSchema, logger: logging.Logger
) -> None:
    """
    Insert data asynchronously into a table using a database connection.

    Parameters
    ----------
    pool : DatabaseConnectionPool
        Database connection pool
    data : str | MultiPersonsSchema
        JSON string or MultiPersonsSchema object containing prediction data

    Raises
    ------
        aiosqlite.Error: If there's an error connecting to the database
    """
    try:
        async with pool.connection() as conn:
            async with transaction(conn):
                if isinstance(data, str):
                    results_list: list[dict[str, Any]] = MultiPersonsSchema.model_validate_json(
                        data
                    ).model_dump()["persons"]
                else:
                    results_list = data.model_dump()["persons"]
                results_list: list[tuple[Any, ...]] = [  # type: ignore
                    _extract_dlq_data(row) for row in results_list
                ]

                await conn.executemany(DLQ_QUERY, results_list)
    except aiosqlite.Error as e:
        logger.error(f"Database error when inserting data: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error when inserting data: {e}")
        raise


def download_file_from_gdrive(file_id: str | Path, destination: str | Path) -> None:
    """This is used to download files from the Google Drive

    Parameters
    ----------
    file_id : str | Path
        The ID of the file to download
    destination : str | Path
        The path to save the downloaded file
    """
    download_url: str = f"https://drive.google.com//uc?export=download&id={file_id}"
    response = requests.get(download_url, stream=True)
    # Raise an exception for bad status codes
    response.raise_for_status()

    with open(destination, "wb") as file:
        for chunk in response.iter_content(chunk_size=8192):
            file.write(chunk)


async def download_file_from_gdrive_async(file_id: str | Path, destination: str | Path) -> None:
    """This is used to asynchronously download files from the Google Drive

    Parameters
    ----------
    file_id : str | Path
        The ID of the file to download
    destination : str | Path
        The path to save the downloaded file
    """
    return await asyncio.to_thread(download_file_from_gdrive, file_id, destination)
