"""
Database connection and schema initialization for SQLite persistent memory.
"""

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Generator
from config import DATABASE_PATH


@contextmanager
def get_db_connection(db_path: str = DATABASE_PATH) -> Generator[sqlite3.Connection, None, None]:
    """Context manager creating a configured SQLite connection that safely closes on exit."""
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA foreign_keys=ON;")
    except sqlite3.DatabaseError:
        pass

    try:
        yield conn
    finally:
        conn.close()


def init_db(db_path: str = DATABASE_PATH) -> None:
    """Initializes tables for research sessions and user preferences."""
    with get_db_connection(db_path) as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS research_sessions (
                session_id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                question TEXT NOT NULL,
                depth TEXT NOT NULL,
                status TEXT NOT NULL,
                error_message TEXT,
                plan_json TEXT,
                sources_json TEXT,
                analysis_json TEXT,
                report_json TEXT,
                full_markdown TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_sessions_created ON research_sessions(created_at DESC);
            CREATE INDEX IF NOT EXISTS idx_sessions_question ON research_sessions(question);

            CREATE TABLE IF NOT EXISTS user_preferences (
                pref_key TEXT PRIMARY KEY,
                pref_value TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            """
        )
        conn.commit()
