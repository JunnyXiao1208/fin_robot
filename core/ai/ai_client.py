# -*- coding: utf-8 -*-
import logging
import os
import asyncio
from typing import Any, List, Optional
from tenacity import (
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    AsyncRetrying
)

from openai import AsyncOpenAI, APIStatusError, APITimeoutError, APIConnectionError

logger = logging.getLogger(__name__)

# 模型配置注册表
MODEL_REGISTRY = {
    "xiaomi": {
        "client_type": "openai",
        "api_key_env": "XIAOMI_API_KEY",
        "base_url_env": "XIAOMI_BASE_URL",
        "default_base_url": "https://token-plan-cn.xiaomimimo.com/v1",
        "model_env": "XIAOMI_MODEL",
        "default_model": "mimo-v2.5-pro",
    },
    "deepseek": {
        "client_type": "openai",
        "api_key_env": "DEEPSEEK_API_KEY",
        "base_url_env": "DEEPSEEK_BASE_URL",
        "default_base_url": "https://api.deepseek.com/v1",
        "model_env": "DEEPSEEK_MODEL",
        "default_model": "deepseek-chat",
    },
    "openrouter": {
        "client_type": "openai",
        "api_key_env": "OPENROUTER_API_KEY",
        "base_url_env": "OPENROUTER_BASE_URL",
        "default_base_url": "https://openrouter.ai/api/v1",
        "model_env": "OPENROUTER_MODEL",
        "default_model": "inclusionai/ring-2.6-1t:free", # 已更新为你指定的模型
    },
}

# 优先级降级序列
FALLBACK_ORDER = ["xiaomi", "deepseek", "openrouter"]

_CLIENT_CACHE: dict[str, Any] = {}

def get_active_provider(provider: str | None = None) -> str:
    return (provider or os.getenv("ACTIVE_MODEL", "xiaomi")).strip().lower()

def get_provider_config(provider: str) -> dict[str, Any]:
    config = MODEL_REGISTRY.get(provider)
    if not config:
        raise ValueError(f"未知模型提供商: {provider}")
    return config

def get_model_name(provider: str, model: str | None = None) -> str:
    if model: return model
    config = get_provider_config(provider)
    env_val = os.getenv(config.get("model_env", ""))
    return env_val or config.get("default_model") or ""

def get_client(provider: str) -> Any:
    if provider in _CLIENT_CACHE:
        return _CLIENT_CACHE[provider]
    
    config = get_provider_config(provider)
    api_key = os.getenv(config["api_key_env"])
    if not api_key:
        logger.error(f"未配置 {provider} 的 API Key")
        return None

    base_url = os.getenv(config["base_url_env"], config["default_base_url"])
    client_kwargs = {"api_key": api_key, "base_url": base_url}
    
    if provider == "openrouter":
        client_kwargs["default_headers"] = {
            "HTTP-Referer": os.getenv("OPENROUTER_SITE_URL", "https://github.com/junnyxiao/fin_robot"),
            "X-Title": "FinRobot"
        }
    
    client = AsyncOpenAI(**client_kwargs)
    _CLIENT_CACHE[provider] = client
    return client

async def _do_single_chat(client: Any, model: str, messages: List[dict]) -> str:
    retryer = AsyncRetrying(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((APITimeoutError, APIConnectionError, APIStatusError)),
        reraise=True
    )
    
    async for attempt in retryer:
        with attempt:
            response = await client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.1,
                max_tokens=2000,
            )
            return response.choices[0].message.content.strip()

async def chat_completion(
    prompt: str, 
    system_msg: str = "", 
    provider: str | None = None, 
    model: str | None = None
) -> str:
    primary_provider = get_active_provider(provider)
    
    attempt_queue = [primary_provider]
    for p in FALLBACK_ORDER:
        if p != primary_provider:
            attempt_queue.append(p)

    messages = []
    if system_msg:
        messages.append({"role": "system", "content": system_msg})
    messages.append({"role": "user", "content": prompt})

    last_error = None
    for current_provider in attempt_queue:
        try:
            client = get_client(current_provider)
            if not client: continue
            
            # 如果是当前首选 provider 且传入了特定 model，则使用该 model；
            # 否则（如触发降级时）使用该 provider 的默认 model 配置
            target_model = get_model_name(current_provider, model if current_provider == primary_provider else None)
            logger.info(f"正在尝试使用 {current_provider} ({target_model})...")
            
            return await _do_single_chat(client, target_model, messages)
            
        except Exception as e:
            last_error = e
            logger.warning(f"{current_provider} 调用失败: {str(e)[:100]}，准备切换...")
            continue
    
    logger.error("所有模型路径均失效")
    raise last_error or Exception("No available AI provider")