"""
job_store.py — SQLite-backed crawl job persistence.

Fixes Issue #16: in-memory crawl_status_dict and parsed_store are lost on
restart. This module persists job state in SQLite so it survives server
restarts and supports multiple workers.

Also addresses Issue #17: stores error tracebacks in the database.
"""

import json
import os
import sqlite3
from datetime import datetime
from typing import Any, Optional

from vector_store import DATA_DIR

DB_PATH = os.path.join(DATA_DIR, "jobs.db")


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def _ensure_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS crawl_jobs (
            job_id     TEXT PRIMARY KEY,
            status     TEXT NOT NULL DEFAULT 'crawling',
            pages      INTEGER NOT NULL DEFAULT 0,
            functions  INTEGER NOT NULL DEFAULT 0,
            error      TEXT,
            message    TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.commit()


# Initialise on import
_conn = _get_conn()
_ensure_table(_conn)


def create_job(job_id: str) -> dict[str, Any]:
    now = datetime.now().isoformat()
    _conn.execute(
        """
        INSERT OR REPLACE INTO crawl_jobs
            (job_id, status, pages, functions, error, message, created_at, updated_at)
        VALUES (?, 'crawling', 0, 0, NULL, NULL, ?, ?)
        """,
        (job_id, now, now),
    )
    _conn.commit()
    return {"status": "crawling", "pages": 0, "functions": 0}


def update_job(
    job_id: str,
    *,
    status: Optional[str] = None,
    pages: Optional[int] = None,
    functions: Optional[int] = None,
    error: Optional[str] = None,
    message: Optional[str] = None,
) -> None:
    parts: list[str] = []
    values: list[Any] = []

    if status is not None:
        parts.append("status = ?")
        values.append(status)
    if pages is not None:
        parts.append("pages = ?")
        values.append(pages)
    if functions is not None:
        parts.append("functions = ?")
        values.append(functions)
    if error is not None:
        parts.append("error = ?")
        values.append(error)
    if message is not None:
        parts.append("message = ?")
        values.append(message)

    if not parts:
        return

    parts.append("updated_at = ?")
    values.append(datetime.now().isoformat())
    values.append(job_id)

    _conn.execute(
        f"UPDATE crawl_jobs SET {', '.join(parts)} WHERE job_id = ?",
        values,
    )
    _conn.commit()


def get_job(job_id: str) -> dict[str, Any]:
    row = _conn.execute(
        "SELECT status, pages, functions, error, message FROM crawl_jobs WHERE job_id = ?",
        (job_id,),
    ).fetchone()

    if row is None:
        return {"status": "not_found"}

    result: dict[str, Any] = {
        "status": row["status"],
        "pages": row["pages"],
        "functions": row["functions"],
    }
    if row["error"]:
        result["error"] = row["error"]
    if row["message"]:
        result["message"] = row["message"]
    return result
