# -*- coding: utf-8 -*-
from typing import Any

FALLBACK_SIGNAL = {
    "source_type": "unknown",
    "author": "",
    "category": "non_financial",
    "sentiment": "中性",
    "importance": 1,
    "confidence": 0.0,
    "horizon": "短期",
    "affected_markets": [],
    "affected_assets": [],
    "affected_sectors": [],
    "tags": ["模型异常"],
    "theme_tags": [],
    "summary": "AI 分析失败",
    "logic": "",
    "risk_points": ["模型输出异常，当前结果已降级为保守值"],
    "risk_level": "高",
    "action_bias": "观望",
}


def default_signal(source_type: str = "news", author: str = "") -> dict[str, Any]:
    return {
        "source_type": source_type,
        "author": author,
        "category": "non_financial",
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


def apply_defaults(signal: dict[str, Any], source_type: str = "news", author: str = "") -> dict[str, Any]:
    defaults = default_signal(source_type=source_type, author=author)
    merged = {**defaults, **signal}
    if merged.get("category") == "non_financial":
        merged.setdefault("sentiment", "中性")
        merged.setdefault("importance", 1)
        merged.setdefault("action_bias", "观望")
        merged.setdefault("risk_level", "低")
    return merged
