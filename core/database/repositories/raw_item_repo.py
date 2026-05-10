# -*- coding: utf-8 -*-
import json
import logging
import sqlite3
from typing import Any

from core.database.db import get_connection, DB_PATH

logger = logging.getLogger(__name__)


def exists(conn: sqlite3.Connection, raw_item: dict) -> bool:
    cursor = conn.execute(
        "SELECT 1 FROM raw_items WHERE source_type = ? AND source_id = ? AND external_id = ? LIMIT 1",
        (raw_item["source_type"], raw_item["source_id"], raw_item["external_id"]),
    )
    if cursor.fetchone():
        return True
    cursor = conn.execute(
        "SELECT 1 FROM raw_items WHERE source_type = ? AND content_hash = ? LIMIT 1",
        (raw_item["source_type"], raw_item["content_hash"]),
    )
    return cursor.fetchone() is not None


def save(conn: sqlite3.Connection, raw_item: dict) -> bool:
    if exists(conn, raw_item):
        return False
    conn.execute(
        """INSERT INTO raw_items (
            item_id, source_type, source_name, source_id, external_id, author,
            title, content, url, published_at, language, content_hash,
            metadata_json, fetched_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            raw_item["item_id"],
            raw_item["source_type"],
            raw_item["source_name"],
            raw_item["source_id"],
            raw_item["external_id"],
            raw_item["author"],
            raw_item["title"],
            raw_item["content"],
            raw_item["url"],
            raw_item["published_at"],
            raw_item["language"],
            raw_item["content_hash"],
            json.dumps(raw_item["metadata"], ensure_ascii=False),
            raw_item["fetched_at"],
        ),
    )
    return True


def query_recent(limit: int = 20, db_path: str = DB_PATH) -> list[dict]:
    conn = get_connection(db_path)
    try:
        rows = conn.execute(
            """SELECT item_id, source_type, source_name, source_id, external_id, author,
                      title, content, url, published_at, language, content_hash,
                      metadata_json, fetched_at
               FROM raw_items ORDER BY fetched_at DESC LIMIT ?""",
            (limit,),
        ).fetchall()
        results = []
        for row in rows:
            item = dict(row)
            item["metadata"] = json.loads(item.pop("metadata_json") or "{}")
            results.append(item)
        return results
    finally:
        conn.close()
