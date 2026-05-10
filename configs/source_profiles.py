# -*- coding: utf-8 -*-
import json
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

SOURCE_CATEGORIES = {
    "36kr": "industry",
    "tmtpost": "industry",
    "bbc_business": "macro",
    "cnbc_finance": "market",
    "wsj_markets": "macro",
    "marketwatch_top": "market",
    "techcrunch": "industry",
    "elonmusk": "industry",
    "CathieDWood": "sentiment",
    "WSJ": "macro",
    "Reuters": "macro",
}

CATEGORY_VALUES = {"macro", "market", "industry", "sentiment", "policy"}
_DEFAULT_CATEGORY = "market"


def _load_custom_profiles() -> dict[str, str]:
    raw = os.getenv("SOURCE_PROFILES_JSON", "").strip()
    if not raw:
        return {}
    try:
        overrides = json.loads(raw)
        if isinstance(overrides, dict):
            return overrides
        return {}
    except json.JSONDecodeError:
        return {}


def get_source_category(source_name: str, source_type_prefix: str = "rss") -> str:
    combined = {**SOURCE_CATEGORIES, **_load_custom_profiles()}
    cat = combined.get(source_name) or combined.get(source_name.lower())
    if cat in CATEGORY_VALUES:
        return cat
    return _DEFAULT_CATEGORY


def attach_source_category(raw_item: dict) -> dict:
    if "metadata" not in raw_item:
        raw_item["metadata"] = {}
    raw_item["metadata"]["source_category"] = get_source_category(
        raw_item.get("source_name", ""),
        raw_item.get("source_type", "rss"),
    )
    return raw_item
