# -*- coding: utf-8 -*-
import json
import re
from typing import Any


FINANCIAL_FILTER_SCHEMA = {
    "is_financial_relevant": True,
    "category": "market",
    "importance": 3,
}

MARKET_SIGNAL_SCHEMA = {
    "category": "macro",
    "sentiment": "中性",
    "importance": 3,
    "confidence": 0.5,
    "horizon": "短期",
    "affected_markets": [],
    "affected_assets": [],
    "affected_sectors": [],
    "tags": [],
    "theme_tags": [],
    "summary": "",
    "logic": "",
    "risk_points": [],
    "risk_level": "低",
    "action_bias": "观望",
}


def extract_json_block(content: str) -> dict[str, Any]:
    content = content.strip()
    if not content:
        raise ValueError("模型返回为空")
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        match = re.search(r"\{[\s\S]*\}", content)
        if not match:
            raise
        return json.loads(match.group(0))


def apply_schema_defaults(signal: dict[str, Any], schema: dict[str, Any]) -> dict[str, Any]:
    merged = {**schema, **signal}
    if merged.get("category") == "non_financial":
        merged.setdefault("sentiment", "中性")
        merged.setdefault("importance", 1)
        merged.setdefault("action_bias", "观望")
        merged.setdefault("risk_level", "低")
    return merged
