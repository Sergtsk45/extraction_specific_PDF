"""
app/llm_client.py
Тонкая обёртка над shared/llm_client для invoice-extractor.
Сохраняет оригинальный публичный API: call_vision_llm(images_b64, prompt, provider).
"""
from __future__ import annotations

import os
import logging

from llm_client import call_vision_llm as _shared_call

logger = logging.getLogger(__name__)

_MODEL_MAP = {
    "anthropic":  lambda: os.getenv("ANTHROPIC_MODEL",  "claude-opus-4-5"),
    "openai":     lambda: os.getenv("OPENAI_MODEL",      "gpt-4o"),
    "openrouter": lambda: os.getenv("OPENROUTER_MODEL",  "anthropic/claude-opus-4-5"),
}


def call_vision_llm(
    images_b64: list[str],
    prompt: str,
    provider: str = "anthropic",
) -> str:
    """
    Отправляет изображения + промпт в LLM.
    Возвращает текстовый ответ модели.
    """
    provider = provider.lower().strip()
    model_getter = _MODEL_MAP.get(provider)
    model = model_getter() if model_getter else None

    return _shared_call(
        images=images_b64,
        prompt=prompt,
        provider=provider,
        model=model,
    )
