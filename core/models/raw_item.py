# -*- coding: utf-8 -*-
import uuid
from datetime import datetime, timezone
from typing import Any


def new_raw_item(
    source_type: str,
    source_name: str,
    source_id: str,
    external_id: str,
    content: str,
    author: str = "",
    title: str = "",
    url: str = "",
    published_at: str = "",
    language: str = "unknown",
    content_hash: str = "",
    metadata: dict | None = None,
) -> dict[str, Any]:
    return {
        "item_id": str(uuid.uuid4()),
        "source_type": source_type,
        "source_name": source_name,
        "source_id": source_id,
        "external_id": external_id,
        "author": author,
        "title": title,
        "content": content,
        "url": url,
        "published_at": published_at,
        "language": language,
        "content_hash": content_hash,
        "metadata": metadata or {},
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }


class RawItem:
    @staticmethod
    def new(**kwargs) -> dict[str, Any]:
        return new_raw_item(**kwargs)
