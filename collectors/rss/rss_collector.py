# -*- coding: utf-8 -*-
import logging
import time
from typing import Any

import feedparser
import requests

from collectors.rss.rss_sources import load_feeds, should_keep
from collectors.rss.rss_normalizer import normalize as normalize_entry

logger = logging.getLogger(__name__)


def fetch_feed(url: str, retries: int = 3, timeout: int = 15):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/rss+xml, application/xml, text/xml",
    }
    for attempt in range(1, retries + 1):
        try:
            response = requests.get(url, headers=headers, timeout=timeout)
            response.raise_for_status()
            feed = feedparser.parse(response.content)
            if feed.bozo:
                logger.warning(f"RSS 解析警告 [{url}]: {feed.bozo_exception}")
            return feed
        except requests.Timeout:
            logger.warning(f"超时 [{url}] 第 {attempt}/{retries} 次重试")
        except requests.RequestException as e:
            logger.warning(f"请求失败 [{url}]: {e}")
        if attempt < retries:
            time.sleep(2 ** attempt)
    logger.error(f"抓取失败 [{url}]，已重试 {retries} 次")
    return None


def collect_raw_items(limit_per_feed: int | None = None, keyword_filter: bool = True, attach_category_fn=None) -> list[dict[str, Any]]:
    all_items = []
    seen_keys = set()

    for feed_config in load_feeds():
        source_name = feed_config["name"]
        feed_url = feed_config["url"]
        logger.info(f"正在抓取 RSS: {source_name} <{feed_url}>")
        feed = fetch_feed(feed_url)
        if not feed or not feed.entries:
            continue

        entry_count = 0
        for entry in feed.entries:
            raw_item = normalize_entry(entry, source_name=source_name, source_id=feed_url)
            if not raw_item:
                continue
            if not should_keep(raw_item["title"], raw_item["content"], keyword_filter=keyword_filter):
                continue
            unique_key = raw_item["external_id"] or raw_item["content_hash"]
            if unique_key in seen_keys:
                continue
            seen_keys.add(unique_key)
            if attach_category_fn:
                attach_category_fn(raw_item)
            all_items.append(raw_item)
            entry_count += 1
            if limit_per_feed and entry_count >= limit_per_feed:
                break
        logger.info(f"[{source_name}] 保留 {entry_count} 条规范化条目")

    logger.info(f"本轮 RSS 共得到 {len(all_items)} 条条目")
    return all_items
