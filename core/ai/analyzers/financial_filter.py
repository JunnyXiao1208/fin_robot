# -*- coding: utf-8 -*-
import logging
from typing import Any

from core.ai.ai_client import chat_completion
from core.ai.prompts.financial_filter_prompt import FINANCIAL_FILTER_PROMPT
from core.ai.prompts.schemas import extract_json_block, FINANCIAL_FILTER_SCHEMA, apply_schema_defaults

logger = logging.getLogger(__name__)


async def analyze(text: str, source_type: str = "news") -> dict[str, Any]:
    prompt = f"{FINANCIAL_FILTER_PROMPT}\n\n待分析文本：\n{text}"
    try:
        content = await chat_completion(prompt, system_msg="你是金融内容过滤器，只能输出合法 JSON。")
        result = extract_json_block(content)
        return apply_schema_defaults(result, FINANCIAL_FILTER_SCHEMA)
    except Exception as e:
        logger.warning(f"金融过滤失败: {e}")
        return {"is_financial_relevant": False, "category": "non_financial", "importance": 1}
