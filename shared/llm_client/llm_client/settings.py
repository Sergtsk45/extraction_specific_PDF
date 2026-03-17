"""Конфигурация LLM-клиента из переменных окружения."""
from __future__ import annotations

import os

DEFAULT_TIMEOUT: int = int(os.getenv("REQUEST_TIMEOUT_SEC", "120"))
DEFAULT_MAX_TOKENS: int = int(os.getenv("MAX_TOKENS", "4096"))

_API_KEY_ENV = {
    "anthropic":  "ANTHROPIC_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
    "openai":     "OPENAI_API_KEY",
}

_DEFAULT_MODELS = {
    "anthropic":  lambda: os.getenv("ANTHROPIC_MODEL",  os.getenv("MODEL_NAME", "claude-opus-4-5")),
    "openrouter": lambda: os.getenv("OPENROUTER_MODEL", os.getenv("MODEL_NAME", "anthropic/claude-opus-4-5")),
    "openai":     lambda: os.getenv("OPENAI_MODEL", "gpt-4o"),
}


def get_api_key(provider: str) -> str | None:
    """Возвращает API-ключ для провайдера из env."""
    env_var = _API_KEY_ENV.get(provider.lower())
    return os.getenv(env_var) if env_var else None


def get_default_model(provider: str) -> str:
    """Возвращает модель по умолчанию для провайдера из env."""
    getter = _DEFAULT_MODELS.get(provider.lower())
    return getter() if getter else ""
