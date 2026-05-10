# -*- coding: utf-8 -*-
import json
import logging
import os
import sqlite3
from datetime import datetime, timezone
from typing import Any
from pathlib import Path

logger = logging.getLogger(__name__)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_project_root = Path(SCRIPT_DIR).parents[1]
_env_db = os.getenv("SQLITE_DB_PATH", "")
if _env_db:
    DB_PATH = _env_db if os.path.isabs(_env_db) else str(_project_root / _env_db)
else:
    DB_PATH = str(_project_root / "data" / "fin_robot.db")


def get_connection(db_path: str = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_database(db_path: str = DB_PATH) -> None:
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS raw_items (
                item_id TEXT PRIMARY KEY,
                source_type TEXT NOT NULL,
                source_name TEXT NOT NULL,
                source_id TEXT NOT NULL,
                external_id TEXT,
                author TEXT,
                title TEXT,
                content TEXT NOT NULL,
                url TEXT,
                published_at TEXT,
                language TEXT,
                content_hash TEXT NOT NULL,
                metadata_json TEXT,
                fetched_at TEXT NOT NULL,
                UNIQUE(source_type, source_id, external_id)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS market_signals (
                signal_id TEXT PRIMARY KEY,
                raw_item_id TEXT NOT NULL UNIQUE,
                source_type TEXT NOT NULL,
                source_name TEXT NOT NULL,
                event_type TEXT,
                sentiment TEXT NOT NULL,
                importance INTEGER NOT NULL,
                confidence REAL NOT NULL,
                horizon TEXT,
                affected_markets_json TEXT,
                affected_symbols_json TEXT,
                tags_json TEXT,
                summary TEXT,
                logic TEXT,
                risk_points_json TEXT,
                action_bias TEXT,
                source_category TEXT,
                category TEXT,
                theme_tags_json TEXT,
                affected_assets_json TEXT,
                affected_sectors_json TEXT,
                risk_level TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY(raw_item_id) REFERENCES raw_items(item_id)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sync_state (
                source_key TEXT PRIMARY KEY,
                last_cursor TEXT,
                last_sync_at TEXT,
                status TEXT,
                error_message TEXT
            )
        """)
        _migrate(conn)
        conn.commit()
    finally:
        conn.close()


def _migrate(conn: sqlite3.Connection) -> None:
    existing = [row[1] for row in conn.execute("PRAGMA table_info(market_signals)").fetchall()]
    migrations = [
        ("category", "TEXT"),
        ("theme_tags_json", "TEXT"),
        ("affected_assets_json", "TEXT"),
        ("affected_sectors_json", "TEXT"),
        ("risk_level", "TEXT"),
        ("source_category", "TEXT"),
    ]
    for col_name, col_type in migrations:
        if col_name not in existing:
            conn.execute(f"ALTER TABLE market_signals ADD COLUMN {col_name} {col_type}")
