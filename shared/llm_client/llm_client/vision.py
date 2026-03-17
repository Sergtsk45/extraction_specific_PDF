"""Вспомогательные функции: PDF → изображения, парсинг JSON-ответов LLM."""
from __future__ import annotations

import json
import logging
import re
from io import BytesIO

logger = logging.getLogger(__name__)


def pdf_to_images(
    pdf_path: str,
    zoom: float = 4.0,
    max_size_bytes: int = 4 * 1024 * 1024,
) -> list[tuple[bytes, str]]:
    """Конвертирует PDF в список изображений (~288 DPI при zoom=4).

    Args:
        pdf_path: путь к PDF-файлу
        zoom: коэффициент масштабирования
        max_size_bytes: максимальный размер PNG; выше — конвертируем в JPEG

    Returns:
        list[(image_bytes, media_type)] где media_type = "image/png" | "image/jpeg"
    """
    import fitz  # PyMuPDF

    doc = fitz.open(pdf_path)
    images: list[tuple[bytes, str]] = []

    for page_num, page in enumerate(doc):
        pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
        img_data = pix.tobytes("png")
        media_type = "image/png"

        if len(img_data) > max_size_bytes:
            try:
                from PIL import Image
                img = Image.open(BytesIO(img_data))
                buf = BytesIO()
                img.save(buf, format="JPEG", quality=92)
                img_data = buf.getvalue()
                media_type = "image/jpeg"
            except ImportError:
                pass

        logger.debug(
            "Стр.%d: %dx%dpx, %dKB (%s)",
            page_num + 1, pix.width, pix.height, len(img_data) // 1024,
            "JPEG" if media_type == "image/jpeg" else "PNG",
        )
        images.append((img_data, media_type))

    doc.close()
    return images


def parse_json_response(response_text: str) -> dict:
    """Парсит JSON из ответа LLM. Устойчив к markdown-обёрткам (```json ... ```).

    Returns:
        Разобранный dict или {} при ошибке парсинга
    """
    json_match = re.search(r"```(?:json)?\s*(.*?)\s*```", response_text, re.DOTALL)
    json_str = json_match.group(1) if json_match else response_text.strip()
    json_str = json_str.strip("\ufeff\u200b\u200c\u200d")

    if not json_str.startswith("{"):
        m = re.search(r"\{.*\}", json_str, re.DOTALL)
        if m:
            json_str = m.group(0)

    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        logger.warning("JSON parse error: %s", e)
        return {}
