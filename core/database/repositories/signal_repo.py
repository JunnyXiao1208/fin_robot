# -*- coding: utf-8 -*-
import json
import logging
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Any

from core.database.db import get_connection, DB_PATH

logger = logging.getLogger(__name__)


def save(conn: sqlite3.Connection, raw_item: dict, signal: dict) -> None:
    conn.execute(
        """INSERT OR REPLACE INTO market_signals (
            signal_id, raw_item_id, source_type, source_name, source_category, event_type,
            sentiment, importance, confidence, horizon, affected_markets_json,
            affected_symbols_json, tags_json, summary, logic, risk_points_json,
            action_bias, category, theme_tags_json, affected_assets_json,
            affected_sectors_json, risk_level, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            str(uuid.uuid4()),
            raw_item["item_id"],
            raw_item["source_type"],
            raw_item["source_name"],
            raw_item.get("metadata", {}).get("source_category", "market"),
            signal.get("event_type", ""),
            signal.get("sentiment", "中性"),
            int(signal.get("importance", 3)),
            float(signal.get("confidence", 0.0)),
            signal.get("horizon", "短期"),
            json.dumps(signal.get("affected_markets", []), ensure_ascii=False),
            json.dumps(signal.get("affected_symbols", []), ensure_ascii=False),
            json.dumps(signal.get("tags", []), ensure_ascii=False),
            signal.get("summary", ""),
            signal.get("logic", ""),
            json.dumps(signal.get("risk_points", []), ensure_ascii=False),
            signal.get("action_bias", "观望"),
            signal.get("category", "non_financial"),
            json.dumps(signal.get("theme_tags", []), ensure_ascii=False),
            json.dumps(signal.get("affected_assets", []), ensure_ascii=False),
            json.dumps(signal.get("affected_sectors", []), ensure_ascii=False),
            signal.get("risk_level", "低"),
            datetime.now(timezone.utc).isoformat(),
        ),
    )


def query_recent(limit: int = 20, db_path: str = DB_PATH) -> list[dict]:
    conn = get_connection(db_path)
    try:
        rows = conn.execute(
            """SELECT signal_id, raw_item_id, source_type, source_name, event_type,
                      sentiment, importance, confidence, horizon, affected_markets_json,
                      affected_symbols_json, tags_json, summary, logic, risk_points_json,
                      action_bias, source_category, category, theme_tags_json,
                      affected_assets_json, affected_sectors_json, risk_level, created_at
               FROM market_signals ORDER BY created_at DESC LIMIT ?""",
            (limit,),
        ).fetchall()
        results = []
        for row in rows:
            signal = dict(row)
            signal["affected_markets"] = json.loads(signal.pop("affected_markets_json") or "[]")
            signal["affected_symbols"] = json.loads(signal.pop("affected_symbols_json") or "[]")
            signal["tags"] = json.loads(signal.pop("tags_json") or "[]")
            signal["risk_points"] = json.loads(signal.pop("risk_points_json") or "[]")
            signal["theme_tags"] = json.loads(signal.pop("theme_tags_json") or "[]")
            signal["affected_assets"] = json.loads(signal.pop("affected_assets_json") or "[]")
            signal["affected_sectors"] = json.loads(signal.pop("affected_sectors_json") or "[]")
            results.append(signal)
        return results
    finally:
        conn.close()


def query_ingested(limit: int = 20, db_path: str = DB_PATH) -> list[dict]:
    conn = get_connection(db_path)
    try:
        rows = conn.execute(
            """SELECT r.item_id, r.source_type, r.source_name, r.title, r.url,
                      r.published_at, r.fetched_at,
                      m.sentiment, m.importance, m.confidence, m.horizon, m.summary,
                      m.action_bias, m.source_category, m.category,
                      m.theme_tags_json, m.affected_assets_json, m.affected_sectors_json,
                      m.risk_level
               FROM raw_items r
               LEFT JOIN market_signals m ON m.raw_item_id = r.item_id
               ORDER BY r.fetched_at DESC LIMIT ?""",
            (limit,),
        ).fetchall()
        results = []
        for row in rows:
            item = dict(row)
            item["theme_tags"] = json.loads(item.pop("theme_tags_json") or "[]")
            item["affected_assets"] = json.loads(item.pop("affected_assets_json") or "[]")
            item["affected_sectors"] = json.loads(item.pop("affected_sectors_json") or "[]")
            results.append(item)
        return results
    finally:
        conn.close()
