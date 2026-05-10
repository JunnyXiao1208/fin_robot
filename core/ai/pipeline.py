# -*- coding: utf-8 -*-
import logging
from typing import Any

from core.ai.analyzers import financial_filter, market_state_analyzer
from core.models.market_signal import apply_defaults, FALLBACK_SIGNAL

logger = logging.getLogger(__name__)


async def extract_market_signal(
    text: str,
    source_type: str = "news",
    author: str | None = None,
    provider: str | None = None,
    model: str | None = None,
) -> dict[str, Any]:
    filter_result = await financial_filter.analyze(text, source_type=source_type)

    if filter_result.get("is_financial_relevant") is False:
        fb = apply_defaults({
            "category": "non_financial",
            "importance": 1,
            "confidence": 0.5,
            "summary": "非金融内容，已过滤",
            "logic": "金融过滤器判定为 non_financial",
        }, source_type=source_type, author=author or "")
        return fb

    signal = await market_state_analyzer.analyze(
        text=text,
        source_type=source_type,
        author=author,
    )
    return signal
