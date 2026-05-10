# -*- coding: utf-8 -*-
"""
ai.py — 保留的兼容入口。
所有新代码应使用 core/ai/ 模块。
"""

import logging
import os
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(*args, **kwargs):
        return False

dotenv_path = Path(__file__).with_name(".env")
if dotenv_path.exists():
    load_dotenv(dotenv_path)

from core.ai.ai_client import get_active_provider, get_client, get_model_name, get_current_model_label, validate_provider_config, MODEL_REGISTRY
from core.ai.pipeline import extract_market_signal
from core.models.market_signal import apply_defaults, default_signal, FALLBACK_SIGNAL
from core.ai.prompts.schemas import extract_json_block as _extract_json_block
from core.ai.prompts.financial_filter_prompt import MARKET_SIGNAL_EXTRACTION_PROMPT

format_signal_report = lambda signal: (
    f"[类别]: {signal.get('category', 'non_financial')}\n"
    f"[市场情绪]: {signal.get('sentiment', '中性')}\n"
    f"[事件强度]: {signal.get('importance', 3)}/5 | 置信度 {signal.get('confidence', 0.5)}\n"
    f"[影响周期]: {signal.get('horizon', '短期')}\n"
    f"[影响对象]: {'、'.join(signal.get('affected_markets', [])[:5]) or '暂无'}\n"
    f"[影响标的]: {'、'.join(signal.get('affected_assets', [])[:5]) or '暂无'}\n"
    f"[影响板块]: {'、'.join(signal.get('affected_sectors', [])[:5]) or '暂无'}\n"
    f"[主题标签]: {'、'.join(signal.get('tags', [])[:5]) or '暂无'}\n"
    f"[市场叙事]: {'、'.join(signal.get('theme_tags', [])[:5]) or '暂无'}\n"
    f"[风险等级]: {signal.get('risk_level', '低')}\n"
    f"[核心摘要]: {signal.get('summary', '暂无')}\n"
    f"[影响逻辑]: {signal.get('logic', '暂无')}\n"
    f"[风险提示]: {'；'.join(signal.get('risk_points', [])[:3]) or '暂无'}\n"
    f"[操作倾向]: {signal.get('action_bias', '观望')}"
)

analye_news = extract_market_signal
