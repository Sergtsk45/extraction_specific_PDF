"""Универсальный LLM Vision клиент: Anthropic, OpenAI, OpenRouter."""
from __future__ import annotations

import base64
import logging
from typing import Union

from .settings import get_api_key, get_default_model, DEFAULT_TIMEOUT, DEFAULT_MAX_TOKENS

logger = logging.getLogger(__name__)


def call_vision_llm(
    images: list[Union[bytes, str]],
    prompt: str,
    provider: str = "anthropic",
    *,
    system_prompt: str | None = None,
    api_key: str | None = None,
    model: str | None = None,
    timeout: int | None = None,
    max_tokens: int | None = None,
    temperature: float = 0.0,
) -> str:
    """Отправляет изображения + промпт в LLM. Возвращает текстовый ответ.

    Args:
        images: список изображений (bytes или base64-строка)
        prompt: пользовательский промпт
        provider: "anthropic" | "openrouter" | "openai"
        system_prompt: системный промпт (опционально)
        api_key: API-ключ (если не задан — читается из env)
        model: имя модели (если не задана — читается из env)
        timeout: таймаут HTTP-запроса в секундах
        max_tokens: максимальное количество токенов в ответе
        temperature: температура генерации

    Returns:
        Текстовый ответ модели

    Raises:
        EnvironmentError: если API-ключ не задан
        ValueError: если указан неизвестный провайдер
        RuntimeError: при ошибке API-провайдера
    """
    provider = provider.lower().strip()
    key = api_key or get_api_key(provider)
    if not key:
        raise EnvironmentError(f"API-ключ для провайдера {provider!r} не задан")

    eff_timeout = timeout if timeout is not None else DEFAULT_TIMEOUT
    eff_max_tokens = max_tokens if max_tokens is not None else DEFAULT_MAX_TOKENS
    eff_model = model or get_default_model(provider)

    # Нормализуем изображения в list[(b64_str, media_type)]
    normalized = [_normalize_image(img) for img in images]

    if provider == "anthropic":
        return _call_anthropic(normalized, prompt, key, eff_model, system_prompt, eff_timeout, eff_max_tokens, temperature)
    elif provider == "openai":
        return _call_openai(normalized, prompt, key, eff_model, system_prompt, eff_timeout, eff_max_tokens, temperature)
    elif provider == "openrouter":
        return _call_openrouter(normalized, prompt, key, eff_model, system_prompt, eff_timeout, eff_max_tokens, temperature)
    else:
        raise ValueError(
            f"Неизвестный провайдер: {provider!r}. Допустимые: anthropic, openai, openrouter"
        )


def _normalize_image(img: Union[bytes, str]) -> tuple[str, str]:
    """Нормализует изображение в (base64_str, media_type)."""
    if isinstance(img, bytes):
        media_type = "image/png" if img[:8] == b"\x89PNG\r\n\x1a\n" else "image/jpeg"
        return base64.b64encode(img).decode(), media_type
    # pre-encoded base64 string — assume JPEG
    return img, "image/jpeg"


def _call_anthropic(
    images: list[tuple[str, str]], prompt: str, api_key: str,
    model: str, system_prompt: str | None, timeout: int, max_tokens: int, temperature: float,
) -> str:
    import anthropic

    client = anthropic.Anthropic(api_key=api_key, timeout=timeout)
    content: list[dict] = []
    for b64, media_type in images:
        content.append({
            "type": "image",
            "source": {"type": "base64", "media_type": media_type, "data": b64},
        })
    content.append({"type": "text", "text": prompt})

    kwargs: dict = dict(
        model=model,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": content}],
        temperature=temperature,
    )
    if system_prompt:
        kwargs["system"] = system_prompt

    response = client.messages.create(**kwargs)
    return response.content[0].text


def _call_openai(
    images: list[tuple[str, str]], prompt: str, api_key: str,
    model: str, system_prompt: str | None, timeout: int, max_tokens: int, temperature: float,
) -> str:
    from openai import OpenAI

    client = OpenAI(api_key=api_key, timeout=timeout)
    content: list[dict] = []
    for b64, media_type in images:
        content.append({
            "type": "image_url",
            "image_url": {"url": f"data:{media_type};base64,{b64}"},
        })
    content.append({"type": "text", "text": prompt})

    messages: list[dict] = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": content})

    response = client.chat.completions.create(
        model=model,
        max_tokens=max_tokens,
        messages=messages,
        temperature=temperature,
    )
    return response.choices[0].message.content


def _call_openrouter(
    images: list[tuple[str, str]], prompt: str, api_key: str,
    model: str, system_prompt: str | None, timeout: int, max_tokens: int, temperature: float,
) -> str:
    import requests

    content: list[dict] = []
    for b64, media_type in images:
        content.append({
            "type": "image_url",
            "image_url": {"url": f"data:{media_type};base64,{b64}"},
        })
    content.append({"type": "text", "text": prompt})

    messages: list[dict] = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": content})

    resp = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={"model": model, "max_tokens": max_tokens, "messages": messages, "temperature": temperature},
        timeout=timeout,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"OpenRouter error {resp.status_code}: {resp.text[:300]}")
    return resp.json()["choices"][0]["message"]["content"]
