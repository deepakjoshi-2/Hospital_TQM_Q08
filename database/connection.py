"""SQLite connection and transaction management for Hospital TQM system."""
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Generator, Optional, Tuple

from config.constants import DEFAULT_DB_PATH


def get_db_path(custom_path: Optional[str] = None) -> str:
    """Return configured database path or default."""
    if custom_path:
        return custom_path
    return os.environ.get("HOSPITAL_DB_PATH", DEFAULT_DB_PATH)


def connect_database(db_path: Optional[str] = None) -> sqlite3.Connection:
    """Create and configure a raw SQLite connection with foreign keys enabled."""
    target_path = get_db_path(db_path)
    
    # Ensure parent directory exists for file-based DBs
    if target_path != ":memory:":
        Path(target_path).parent.mkdir(parents=True, exist_ok=True)
        
    conn = sqlite3.connect(target_path, timeout=10.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    if target_path != ":memory:":
        conn.execute("PRAGMA journal_mode = WAL;")
    return conn


@contextmanager
def get_db_connection(db_path: Optional[str] = None) -> Generator[sqlite3.Connection, None, None]:
    """Context manager yielding an active database connection and closing it safely."""
    conn = connect_database(db_path)
    try:
        yield conn
    finally:
        conn.close()


@contextmanager
def get_db_cursor(db_path: Optional[str] = None) -> Generator[Tuple[sqlite3.Connection, sqlite3.Cursor], None, None]:
    """Context manager yielding (conn, cursor) with automatic commit or rollback."""
    conn = connect_database(db_path)
    cursor = conn.cursor()
    try:
        yield conn, cursor
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()


def init_db(db_path: Optional[str] = None, schema_file: Optional[str] = None) -> None:
    """Initialize the database by executing the schema DDL script."""
    if schema_file is None:
        schema_file = str(Path(__file__).resolve().parent / "schema.sql")

    with open(schema_file, "r", encoding="utf-8") as f:
        schema_sql = f.read()

    with get_db_connection(db_path) as conn:
        conn.executescript(schema_sql)
        conn.commit()


def reset_db(db_path: Optional[str] = None) -> None:
    """Safely drop all existing tables and re-initialize with fresh schema."""
    drop_tables_script = """
    PRAGMA foreign_keys = OFF;
    DROP TABLE IF EXISTS receipts;
    DROP TABLE IF EXISTS payments;
    DROP TABLE IF EXISTS bills;
    DROP TABLE IF EXISTS notifications;
    DROP TABLE IF EXISTS users;
    DROP TABLE IF EXISTS tqm_fmea_records;
    DROP TABLE IF EXISTS tqm_defect_logs;
    DROP TABLE IF EXISTS appointments;
    DROP TABLE IF EXISTS doctors;
    DROP TABLE IF EXISTS patients;
    DROP TABLE IF EXISTS user_profile;
    PRAGMA foreign_keys = ON;
    """
    with get_db_connection(db_path) as conn:
        conn.executescript(drop_tables_script)
        conn.commit()
    init_db(db_path)
