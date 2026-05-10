# -*- coding: utf-8 -*-
import logging
from typing import Any

from core.database.db import init_database
from core.database.repositories import raw_item_repo, signal_repo, market_state_repo as sync_repo
from core.ai.pipeline import extract_market_signal

logger = logging.getLogger(__name__)


async def ingest_rss_items(limit_per_feed: int | None = None, keyword_filter: bool = True) -> dict:
    init_database()

    from configs.source_profiles import attach_source_category
    from collectors.rss.rss_collector import collect_raw_items

    raw_items = collect_raw_items(
        limit_per_feed=limit_per_feed,
        keyword_filter=keyword_filter,
        attach_category_fn=attach_source_category,
    )
    stats = {"fetched": len(raw_items), "saved": 0, "signals": 0, "skipped": 0}

    from core.database.db import DB_PATH
    import sqlite3

    conn = sqlite3.connect(DB_PATH)
    try:
        for raw_item in raw_items:
            saved = raw_item_repo.save(conn, raw_item)
            if not saved:
                stats["skipped"] += 1
                continue
            stats["saved"] += 1

            signal = await extract_market_signal(
                text=raw_item["content"],
                source_type=raw_item["source_type"],
                author=raw_item.get("author", ""),
            )
            signal_repo.save(conn, raw_item, signal)
            stats["signals"] += 1

        sync_repo.save(conn, source_key="rss:default", status="ok", last_cursor=str(stats["saved"]))
        conn.commit()
        logger.info(f"RSS 闭环完成: {stats}")
        return stats
    except Exception as e:
        conn.rollback()
        sync_repo.save(conn, source_key="rss:default", status="error", error_message=str(e)[:300])
        conn.commit()
        logger.error(f"RSS 入库失败: {e}")
        raise
    finally:
        conn.close()
