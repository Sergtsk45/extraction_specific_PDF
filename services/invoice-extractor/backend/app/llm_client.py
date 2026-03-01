"""
app/llm_client.py
Единый клиент для вызова LLM Vision API.
Поддерживает: Anthropic, OpenAI, OpenRouter.
"""
from __future__ import annotations

import os
import logging

logger = logging.getLogger(__name__)

ANTHROPIC_MODEL   = os.getenv("ANTHROPIC_MODEL",   "claude-opus-4-5")
OPENAI_MODEL      = os.getenv("OPENAI_MODEL",      "gpt-4o")
OPENROUTER_MODEL  = os.getenv("OPENROUTER_MODEL",  "anthropic/claude-opus-4-5")
TIMEOUT           = int(os.getenv("REQUEST_TIMEOUT_SEC", 120))
MAX_TOKENS        = 4096


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

    if provider == "anthropic":
        return _call_anthropic(images_b64, prompt)
    elif provider == "openai":
        return _call_openai(images_b64, prompt)
    elif provider == "openrouter":
        return _call_openrouter(images_b64, prompt)
    else:
        raise ValueError(f"Неизвестный провайдер: {provider!r}. "
                         "Допустимые значения: anthropic, openai, openrouter")


# ── Anthropic ────────────────────────────────────────────────

def _call_anthropic(images_b64: list[str], prompt: str) -> str:
    import anthropic

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise EnvironmentError("ANTHROPIC_API_KEY не задан")

    client = anthropic.Anthropic(api_key=api_key)

    content: list[dict] = []
    for img_b64 in images_b64:
        content.append({
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": "image/jpeg",
                "data": img_b64,
            },
        })
    content.append({"type": "text", "text": prompt})

    response = client.messages.create(
        model=ANTHROPIC_MODEL,
        max_tokens=MAX_TOKENS,
        messages=[{"role": "user", "content": content}],
        timeout=TIMEOUT,
    )
    return response.content[0].text


# ── OpenAI ───────────────────────────────────────────────────

def _call_openai(images_b64: list[str], prompt: str) -> str:
    from openai import OpenAI

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise EnvironmentError("OPENAI_API_KEY не задан")

    client = OpenAI(api_key=api_key, timeout=TIMEOUT)

    content: list[dict] = []
    for img_b64 in images_b64:
        content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"},
        })
    content.append({"type": "text", "text": prompt})

    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        max_tokens=MAX_TOKENS,
        messages=[{"role": "user", "content": content}],
    )
    return response.choices[0].message.content


# ── OpenRouter ───────────────────────────────────────────────

def _call_openrouter(images_b64: list[str], prompt: str) -> str:
    import requests

    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise EnvironmentError("OPENROUTER_API_KEY не задан")

    content: list[dict] = []
    for img_b64 in images_b64:
        content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"},
        })
    content.append({"type": "text", "text": prompt})

    payload = {
        "model": OPENROUTER_MODEL,
        "max_tokens": MAX_TOKENS,
        "messages": [{"role": "user", "content": content}],
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://invoice-parser.local",
    }

    resp = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        json=payload,
        headers=headers,
        timeout=TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]
