# -*- coding: utf-8 -*-
import sqlite3
from datetime import datetime, timezone
from typing import Any

from core.database.db import get_connection, DB_PATH


def save(conn: sqlite3.Connection, source_key: str, status: str, last_cursor: str = "", error_message: str = "") -> None:
    conn.execute(
        """INSERT INTO sync_state (source_key, last_cursor, last_sync_at, status, error_message)
           VALUES (?, ?, ?, ?, ?)
           ON CONFLICT(source_key) DO UPDATE SET
               last_cursor = excluded.last_cursor,
               last_sync_at = excluded.last_sync_at,
               status = excluded.status,
               error_message = excluded.error_message""",
        (source_key, last_cursor, datetime.now(timezone.utc).isoformat(), status, error_message),
    )
