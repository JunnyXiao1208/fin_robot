# -*- coding: utf-8 -*-
import logging
from typing import Any

from core.ai.ai_client import chat_completion
from core.ai.prompts.financial_filter_prompt import MARKET_SIGNAL_EXTRACTION_PROMPT
from core.ai.prompts.schemas import extract_json_block, MARKET_SIGNAL_SCHEMA, apply_schema_defaults
from core.models.market_signal import FALLBACK_SIGNAL

logger = logging.getLogger(__name__)


async def analyze(
    text: str,
    source_type: str = "news",
    author: str | None = None,
) -> dict[str, Any]:
    author_text = author or ""
    prompt = f"{MARKET_SIGNAL_EXTRACTION_PROMPT}\n\nsource_type: {source_type}\nauthor: {author_text}\n\n待分析文本：\n{text}"

    try:
        content = await chat_completion(
            prompt,
            system_msg="你是金融文本结构化提取引擎，只能输出合法 JSON。",
        )
        result = extract_json_block(content)
        result["source_type"] = source_type
        result["author"] = author_text
        return apply_schema_defaults(result, MARKET_SIGNAL_SCHEMA)
    except Exception as e:
        logger.error(f"AI 信号提取失败: {e}")
        fb = dict(FALLBACK_SIGNAL)
        fb["source_type"] = source_type
        fb["author"] = author_text
        fb["summary"] = f"AI 分析失败: {str(e)[:100]}"
        fb["logic"] = str(e)[:200]
        return fb
