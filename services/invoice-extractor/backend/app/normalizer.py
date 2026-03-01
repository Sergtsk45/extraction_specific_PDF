"""
app/normalizer.py
Нормализация и очистка данных счёта после извлечения.
"""
from __future__ import annotations

import re
from typing import Any


def normalize_invoice(data: dict) -> dict:
    """Приводит данные счёта к стандартному виду."""
    data = dict(data)

    # Числовые поля в итогах
    totals = data.get("totals", {})
    data["totals"] = {
        "total_wo_vat": _to_float(totals.get("total_wo_vat", "")),
        "vat_total":    _to_float(totals.get("vat_total",    "")),
        "total_w_vat":  _to_float(totals.get("total_w_vat",  "")),
    }

    # Нормализация строк items
    items = data.get("items", [])
    normalized_items = []
    for i, item in enumerate(items, 1):
        if not isinstance(item, dict):
            continue
        normalized_items.append({
            "line_no":       item.get("line_no") or i,
            "article":       _clean_str(item.get("article", "")),
            "name":          _clean_str(item.get("name", "")),
            "unit":          _clean_str(item.get("unit", "")),
            "qty":           _to_float(item.get("qty", "")),
            "price":         _to_float(item.get("price", "")),
            "amount_wo_vat": _to_float(item.get("amount_wo_vat", "")),
            "discount":      _to_float(item.get("discount", "")),
            "vat_rate":      _normalize_vat_rate(item.get("vat_rate", "")),
            "vat_amount":    _to_float(item.get("vat_amount", "")),
            "amount_w_vat":  _to_float(item.get("amount_w_vat", "")),
        })
    data["items"] = normalized_items

    # Строковые поля шапки
    for party in ("supplier", "buyer"):
        p = data.get(party, {})
        if isinstance(p, dict):
            p["name"]    = _clean_str(p.get("name", ""))
            p["inn"]     = _digits_only(p.get("inn", ""))
            p["kpp"]     = _digits_only(p.get("kpp", ""))
            p["address"] = _clean_str(p.get("address", ""))

    bank = data.get("supplier", {}).get("bank", {})
    if isinstance(bank, dict):
        bank["bik"]          = _digits_only(bank.get("bik", ""))
        bank["account"]      = _digits_only(bank.get("account", ""))
        bank["corr_account"] = _digits_only(bank.get("corr_account", ""))

    # Дата
    data["invoice_date"] = _normalize_date_str(data.get("invoice_date", ""))

    return data


# ── Утилиты ───────────────────────────────────────────────────

def _to_float(value: Any) -> float | str:
    if value is None or value == "":
        return ""
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value).replace("\u00a0", "").replace(" ", "").replace(",", ".")
    s = re.sub(r"[^\d.]", "", s)
    try:
        return float(s)
    except ValueError:
        return ""


def _clean_str(value: Any) -> str:
    if not value:
        return ""
    return " ".join(str(value).split())


def _digits_only(value: Any) -> str:
    if not value:
        return ""
    return re.sub(r"\D", "", str(value))


def _normalize_vat_rate(raw: Any) -> str:
    if not raw:
        return ""
    r = str(raw).lower().strip()
    if "без" in r or "не облагается" in r or r in ("0", "-", ""):
        return "без НДС"
    m = re.search(r"\d+", r)
    return m.group() + "%" if m else str(raw)


_DATE_RU = {
    "января": "01", "февраля": "02", "марта": "03", "апреля": "04",
    "мая": "05", "июня": "06", "июля": "07", "августа": "08",
    "сентября": "09", "октября": "10", "ноября": "11", "декабря": "12",
}


def _normalize_date_str(raw: str) -> str:
    if not raw or re.match(r"\d{4}-\d{2}-\d{2}", raw):
        return raw  # уже нормализовано
    s = str(raw).replace("г.", "").strip()
    for ru, num in _DATE_RU.items():
        s = s.replace(ru, num)
    parts = re.split(r"[\s./]+", s)
    parts = [p for p in parts if p and p.isdigit()]
    if len(parts) == 3:
        d, m, y = parts
        if len(y) == 2:
            y = "20" + y
        return f"{y}-{m.zfill(2)}-{d.zfill(2)}"
    return raw
