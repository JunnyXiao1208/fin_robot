# -*- coding: utf-8 -*-
import json
import hashlib
import logging
import os
import re
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse, urlunparse

from core.utils.time_utils import to_iso_datetime
from core.models.raw_item import new_raw_item

logger = logging.getLogger(__name__)


def clean_html(text: str) -> str:
    text = re.sub(r"<[^>]+>", "", text or "")
    text = text.replace("&nbsp;", " ").replace("&amp;", "&").replace("&#39;", "'")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def clean_link(link: str) -> str:
    parsed = urlparse(link or "")
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", "", ""))


def detect_language(text: str) -> str:
    if re.search(r"[\u4e00-\u9fff]", text or ""):
        return "zh"
    if re.search(r"[A-Za-z]", text or ""):
        return "en"
    return "unknown"


def build_content_hash(source_type: str, source_name: str, title: str, content: str) -> str:
    payload = f"{source_type}|{source_name}|{title.strip()}|{content.strip()[:500]}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def normalize(entry: dict, source_name: str, source_id: str, attach_category_fn=None) -> dict | None:
    title = entry.get("title", "").strip()
    try:
        title = title.encode("latin1").decode("utf-8")
    except (UnicodeDecodeError, UnicodeEncodeError):
        pass

    raw_summary = entry.get("summary", entry.get("description", ""))
    content = clean_html(raw_summary)[:2000]
    if not content and not title:
        return None

    link = clean_link(entry.get("link", ""))
    published_at = to_iso_datetime(entry)
    tags = []
    for tag in entry.get("tags", []):
        if isinstance(tag, dict):
            term = str(tag.get("term", "")).strip()
        else:
            term = str(getattr(tag, "term", "")).strip()
        if term:
            tags.append(term)

    external_id = str(entry.get("id", "")).strip() or link or f"{title}|{published_at}"
    language = detect_language(f"{title}\n{content}")
    content_hash = build_content_hash("rss", source_name, title, content)

    result = new_raw_item(
        source_type="rss",
        source_name=source_name,
        source_id=source_id,
        external_id=external_id,
        author=clean_html(entry.get("author", ""))[:120],
        title=title[:300],
        content=content,
        url=link,
        published_at=published_at,
        language=language,
        content_hash=content_hash,
        metadata={"feed_title": source_name, "tags": tags},
    )
    if attach_category_fn:
        attach_category_fn(result)
    return result
