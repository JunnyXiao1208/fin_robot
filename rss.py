# -*- coding: utf-8 -*-
"""
rss.py — 保留的兼容入口。
所有新代码应使用 collectors/rss/ + services/ + core/database/。
"""

import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import asyncio
import json
import logging
import sqlite3

logger = logging.getLogger(__name__)

from configs.settings import DB_PATH, PROJECT_ROOT
from core.database.db import init_database as _init_db
from core.database.repositories import raw_item_repo, signal_repo, market_state_repo as sync_repo
from configs.source_profiles import attach_source_category

SCRIPT_DIR = str(PROJECT_ROOT)

# 导出旧接口
load_rss_feeds = __import__("collectors.rss.rss_sources", fromlist=["load_feeds"]).load_feeds
load_rss_feeds.__name__ = "load_rss_feeds"

from collectors.rss.rss_normalizer import (
    detect_language,
    build_content_hash,
    clean_html,
    clean_link,
)
from collectors.rss.rss_sources import TARGET_KEYWORDS
should_keep_entry = __import__("collectors.rss.rss_sources", fromlist=["should_keep"]).should_keep
from collectors.rss.rss_collector import fetch_feed

TARGET_KEYWORDS = __import__("collectors.rss.rss_sources", fromlist=["TARGET_KEYWORDS"]).TARGET_KEYWORDS

# 重新导出旧接口
def get_recent_raw_items(limit=20, db_path=None):
    return raw_item_repo.query_recent(limit=limit, db_path=db_path or DB_PATH)

def get_recent_market_signals(limit=20, db_path=None):
    return signal_repo.query_recent(limit=limit, db_path=db_path or DB_PATH)

def get_recent_ingested_items(limit=20, db_path=None):
    return signal_repo.query_ingested(limit=limit, db_path=db_path or DB_PATH)

def init_rss_db(db_path=None):
    _init_db(db_path=db_path or DB_PATH)

def raw_item_exists(conn, raw_item):
    return raw_item_repo.exists(conn, raw_item)

def save_raw_item(conn, raw_item):
    return raw_item_repo.save(conn, raw_item)

def save_market_signal(conn, raw_item, signal):
    return signal_repo.save(conn, raw_item, signal)

def update_sync_state(conn, source_key, status, last_cursor="", error_message=""):
    return sync_repo.save(conn, source_key, status, last_cursor, error_message)

def should_keep_entry(title, content, keyword_filter=True):
    from collectors.rss.rss_sources import should_keep
    return should_keep(title, content, keyword_filter)

def normalize_rss_entry(entry, source_name, source_id):
    from collectors.rss.rss_normalizer import normalize
    item = normalize(entry, source_name, source_id)
    if item:
        attach_source_category(item)
    return item

def collect_rss_raw_items(limit_per_feed=None, keyword_filter=True):
    from collectors.rss.rss_collector import collect_raw_items
    return collect_raw_items(
        limit_per_feed=limit_per_feed,
        keyword_filter=keyword_filter,
        attach_category_fn=attach_source_category,
    )


async def ingest_rss_items(limit_per_feed=None, keyword_filter=True):
    from services.ingestion_service import ingest_rss_items as _ingest
    return await _ingest(limit_per_feed=limit_per_feed, keyword_filter=keyword_filter)
