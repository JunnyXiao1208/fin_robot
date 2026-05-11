# -*- coding: utf-8 -*-
import logging
from typing import Any

from core.database.db import init_database
from core.database.repositories import raw_item_repo, signal_repo, market_state_repo as sync_repo
from core.ai.pipeline import extract_market_signal

logger = logging.getLogger(__name__)


async def ingest_rss_items(limit_per_feed: int | None = None, keyword_filter: bool = True) -> dict:
    import asyncio
    from dotenv import load_dotenv
    load_dotenv()

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
    saved_items = []
    try:
        for raw_item in raw_items:
            saved = raw_item_repo.save(conn, raw_item)
            if not saved:
                stats["skipped"] += 1
                continue
            stats["saved"] += 1
            saved_items.append(raw_item)
        conn.commit()
        logger.info(f"原始入库完成: 新增 {stats['saved']} 条")
    except Exception as e:
        conn.rollback()
        sync_repo.save(conn, source_key="rss:default", status="error", error_message=str(e)[:300])
        conn.commit()
        logger.error(f"原始入库失败: {e}")
        raise
    finally:
        conn.close()

    if not saved_items:
        logger.info(f"RSS 闭环完成: {stats}")
        return stats

    sem = asyncio.Semaphore(5)

    async def _extract_with_semaphore(raw_item: dict) -> tuple[dict, dict | None]:
        async with sem:
            try:
                signal = await asyncio.wait_for(
                    extract_market_signal(
                        text=raw_item["content"],
                        source_type=raw_item["source_type"],
                        author=raw_item.get("author", ""),
                    ),
                    timeout=45.0,
                )
                return raw_item, signal
            except (TimeoutError, asyncio.exceptions.TimeoutError) as e:
                logger.error(f"AI提取超时 [{raw_item.get('title', '')[:30]}]: {e}")
                return raw_item, None
            except Exception as e:
                logger.error(f"信号提取失败 [{raw_item.get('title', '')[:30]}]: {e}")
                return raw_item, None

    tasks = [_extract_with_semaphore(item) for item in saved_items]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    signal_conn = sqlite3.connect(DB_PATH)
    try:
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"信号提取异常: {result}")
                stats["skipped"] += 1
                continue
            raw_item, signal = result
            if signal is None:
                stats["skipped"] += 1
                continue
            signal_repo.save(signal_conn, raw_item, signal)
            stats["signals"] += 1

        sync_repo.save(signal_conn, source_key="rss:default", status="ok", last_cursor=str(stats["saved"]))
        signal_conn.commit()
        logger.info(f"RSS 闭环完成: {stats}")
        return stats
    except Exception as e:
        signal_conn.rollback()
        sync_repo.save(signal_conn, source_key="rss:default", status="error", error_message=str(e)[:300])
        signal_conn.commit()
        logger.error(f"信号入库失败: {e}")
        raise
    finally:
        signal_conn.close()
