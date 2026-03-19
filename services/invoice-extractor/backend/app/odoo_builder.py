"""
app/odoo_builder.py
Формирование XLSX для импорта товаров в Odoo (шаблон продуктов).
Лист «Template»: 9 колонок по стандарту Odoo product import.
"""
from __future__ import annotations

import logging

from openpyxl import Workbook

logger = logging.getLogger(__name__)

ODOO_HEADERS = [
    "External ID",
    "Name",
    "Product Type",
    "Internal Reference",
    "Barcode",
    "Sales Price",
    "Cost",
    "Weight",
    "Sales Description",
]


def build_odoo_xlsx(data: dict, output_path: str) -> None:
    """Строит XLSX для импорта товаров в Odoo.

    Args:
        data: Извлечённые данные счёта (структура invoice_data).
        output_path: Путь для сохранения файла.
    """
    wb = Workbook()
    ws = wb.active
    ws.title = "Template"

    ws.append(ODOO_HEADERS)

    invoice_num = data.get("invoice_number") or "unknown"
    supplier = data.get("supplier") or {}
    inn = supplier.get("inn") or "x"
    items = data.get("items") or []

    for idx, item in enumerate(items, start=1):
        line_no = item.get("line_no") or idx
        qty = item.get("qty") or 0
        price = item.get("price") or 0

        parts = []
        if item.get("unit"):
            parts.append(f"Ед.: {item['unit']}")
        if item.get("vat_rate") is not None and item.get("vat_rate") != "":
            parts.append(f"НДС: {item['vat_rate']}%")
        if qty:
            parts.append(f"Кол-во: {qty}")

        ws.append([
            f"inv_{inn}_{invoice_num}_{line_no}",  # External ID
            (item.get("name") or "").strip(),       # Name
            "Goods",                                 # Product Type
            item.get("article") or "",               # Internal Reference
            "",                                      # Barcode
            "",                                      # Sales Price (не заполняем)
            price,                                   # Cost
            "",                                      # Weight
            "\n".join(parts),                        # Sales Description
        ])

    wb.save(output_path)
    logger.info("Odoo XLSX saved: %s, rows: %d", output_path, len(items))
