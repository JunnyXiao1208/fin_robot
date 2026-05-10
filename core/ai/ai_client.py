# -*- coding: utf-8 -*-
import logging
import os
from typing import Any

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(*args, **kwargs):
        return False

logger = logging.getLogger(__name__)

MODEL_REGISTRY = {
    "openrouter": {
        "client_type": "openai",
        "api_key_env": "OPENROUTER_API_KEY",
        "base_url_env": "OPENROUTER_BASE_URL",
        "default_base_url": "https://openrouter.ai/api/v1",
        "model_env": "OPENROUTER_MODEL",
    },
    "zhipu": {
        "client_type": "openai",
        "api_key_env": "ZHIPU_API_KEY",
        "base_url_env": "ZHIPU_BASE_URL",
        "default_base_url": "https://open.bigmodel.cn/api/paas/v4",
        "model_env": "ZHIPU_MODEL",
        "default_model": "glm-4.5-air",
    },
    "deepseek": {
        "client_type": "openai",
        "api_key_env": "DEEPSEEK_API_KEY",
        "base_url_env": "DEEPSEEK_BASE_URL",
        "default_base_url": "https://api.deepseek.com/v1",
        "model_env": "DEEPSEEK_MODEL",
        "default_model": "deepseek-chat",
    },
    "volcengine": {
        "client_type": "ark",
        "api_key_env": "VOLCENGINE_API_KEY",
        "base_url_env": "VOLCENGINE_BASE_URL",
        "default_base_url": "https://ark.cn-beijing.volces.com/api/v3",
        "model_env": "VOLCENGINE_ENDPOINT_ID",
    },
}

_CLIENT_CACHE: dict[str, Any] = {}


def get_active_provider(provider: str | None = None) -> str:
    return (provider or os.getenv("ACTIVE_MODEL", "zhipu")).strip().lower()


def get_provider_config(provider: str | None = None) -> dict[str, Any]:
    active_provider = get_active_provider(provider)
    config = MODEL_REGISTRY.get(active_provider)
    if not config:
        supported = ", ".join(MODEL_REGISTRY.keys())
        raise ValueError(f"未知模型提供商: {active_provider}，可选值: {supported}")
    return config


def get_model_name(provider: str | None = None, model: str | None = None) -> str:
    if model:
        return model
    config = get_provider_config(provider)
    model_env = config.get("model_env")
    if model_env:
        env_value = os.getenv(model_env)
        if env_value:
            return env_value
    default_model = config.get("default_model")
    if default_model:
        return default_model
    raise ValueError(f"{get_active_provider(provider)} 缺少模型配置")


def get_current_model_label() -> str:
    provider = get_active_provider()
    try:
        return f"{provider} / {get_model_name(provider=provider)}"
    except Exception:
        return provider


def _missing_required_envs(provider: str | None = None) -> list[str]:
    config = get_provider_config(provider)
    missing = []
    if not os.getenv(config["api_key_env"]):
        missing.append(config["api_key_env"])
    return missing


def get_client(provider: str | None = None) -> Any:
    active_provider = get_active_provider(provider)
    if active_provider in _CLIENT_CACHE:
        return _CLIENT_CACHE[active_provider]
    config = get_provider_config(active_provider)
    missing = _missing_required_envs(active_provider)
    if missing:
        raise ValueError(f"{active_provider} 缺少环境变量: {missing}")
    api_key = os.getenv(config["api_key_env"])
    base_url = os.getenv(config["base_url_env"], config["default_base_url"])
    if config["client_type"] == "ark":
        from volcenginesdkarkruntime import AsyncArk
        client = AsyncArk(api_key=api_key, base_url=base_url)
    else:
        from openai import AsyncOpenAI
        client_kwargs = {"api_key": api_key, "base_url": base_url}
        if active_provider == "openrouter":
            default_headers = {}
            referer = os.getenv("OPENROUTER_SITE_URL", "").strip()
            title = os.getenv("OPENROUTER_APP_NAME", "").strip()
            if referer:
                default_headers["HTTP-Referer"] = referer
            if title:
                default_headers["X-Title"] = title
            if default_headers:
                client_kwargs["default_headers"] = default_headers
        client = AsyncOpenAI(**client_kwargs)
    _CLIENT_CACHE[active_provider] = client
    return client


async def chat_completion(prompt: str, system_msg: str = "", provider: str | None = None, model: str | None = None) -> str:
    client = get_client(provider)
    messages = []
    if system_msg:
        messages.append({"role": "system", "content": system_msg})
    messages.append({"role": "user", "content": prompt})
    response = await client.chat.completions.create(
        model=get_model_name(provider=provider, model=model),
        messages=messages,
        temperature=0.2,
        max_tokens=900,
    )
    return response.choices[0].message.content.strip()
