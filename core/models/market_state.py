# -*- coding: utf-8 -*-
from typing import Any

FALLBACK_MARKET_STATE = {
    "state_id": "",
    "overall_sentiment": "中性",
    "total_signals": 0,
    "bullish_count": 0,
    "bearish_count": 0,
    "neutral_count": 0,
    "top_themes": [],
    "top_assets": [],
    "top_sectors": [],
    "risk_level": "低",
    "macro_score": 0.0,
    "market_score": 0.0,
    "industry_score": 0.0,
    "sentiment_score": 0.0,
    "policy_score": 0.0,
}


class MarketState:
    pass
