# Task Tracker — Odoo output (invoice-extractor)
> **Создано:** 2026-03-19
> **Задача:** Добавить отдельный output для импорта товаров в Odoo (шаблон товаров)
> **Сервис:** `services/invoice-extractor`

---

## Задача: ODOO-001 — Экспорт товаров в формате Odoo Template (9 колонок)
- **Статус**: Выполнено ✓ (2026-03-19)
- **Приоритет**: Высокий
- **Описание**: Добавить новый output-режим в `invoice-extractor`, который формирует файл для импорта товаров в Odoo по шаблону (колонки: External ID, Name, Product Type, Internal Reference, Barcode, Sales Price, Cost, Weight, Sales Description). Источник данных — извлечённые позиции счёта (`items`) из текущего пайплайна.

### Принятые решения (2026-03-19)
- **Формат файла**: `.xlsx` (openpyxl — уже есть в зависимостях, не нужно добавлять xlwt)
- **Имя output-режима**: `odoo_xlsx`
- **Контракт ответа API**: возврат файла (аналогично `output=xlsx`)
- **Sales Price**: цена с НДС за единицу = `round(amount_w_vat / qty, 2)` (fallback `0` при `qty=0`)
- **Product Type**: всегда `Goods` на первом этапе (без эвристик Service)
- **External ID**: `inv_{inn_supplier}_{invoice_number}_{line_no}` — префикс ИНН снижает коллизии между поставщиками

---

## Шаги выполнения

### ODOO-001.1 — Сверить шаблон `obrazec/product_template.xls`
**Статус:** [x] Выполнено
**Файл:** `obrazec/product_template.xls`
**Что проверить:**
- Имя листа: `Template` (уже подтверждено)
- 9 заголовков в строке 0 (подтверждено): `External ID | Name | Product Type | Internal Reference | Barcode | Sales Price | Cost | Weight | Sales Description`
- Нет скрытых колонок/строк между ними
- Формат ячеек (числа vs строки — важно для Sales Price/Cost)

---

### ODOO-001.2 — Спроектировать маппинг полей
**Статус:** [x] Выполнено
**Описание:** Финализировать таблицу маппинга перед кодингом.

| Odoo колонка       | Источник                            | Правила                                              |
|--------------------|-------------------------------------|------------------------------------------------------|
| External ID        | `inv_{inn}_{invoice_number}_{line_no}` | Детерминированный. ИНН из `data["supplier"]["inn"]`, fallback "x" |
| Name               | `item["name"]`                      | Напрямую, strip()                                    |
| Product Type       | Хардкод `"Goods"`                   | Всегда. Расширение на Service — в будущем            |
| Internal Reference | `item["article"]`                   | Пусто если отсутствует                               |
| Barcode            | Пусто `""`                          | В РФ-счетах нет                                     |
| Sales Price        | `round(amount_w_vat / qty, 2)`      | Защита от ZeroDivisionError: если qty=0, ставить 0   |
| Cost               | `item["price"]`                     | Закупочная цена из счёта                             |
| Weight             | Пусто `""`                          | В счетах нет веса                                    |
| Sales Description  | `f"Ед.: {unit}\nНДС: {vat_rate}%\nКол-во: {qty}"` | Только непустые части через \n |

**Поля invoice_data (текущая структура):**
```python
# Верхний уровень:
data["invoice_number"], data["supplier"]["inn"], data["supplier"]["name"]
# Каждый item:
item["line_no"], item["article"], item["name"], item["unit"],
item["qty"], item["price"], item["discount"], item["vat_rate"],
item["vat_amount"], item["amount_w_vat"]
```

---

### ODOO-001.3 — Реализовать `app/odoo_builder.py`
**Статус:** [x] Выполнено
**Файл:** `services/invoice-extractor/backend/app/odoo_builder.py`
**Сигнатура:** `build_odoo_xlsx(data: dict, output_path: str) -> None`

**Структура модуля:**
```python
"""Формирование XLSX для импорта товаров в Odoo."""
from __future__ import annotations
import logging
from pathlib import Path
import openpyxl

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
        data: Извлечённые данные счёта (invoice_data от extract_invoice).
        output_path: Путь для сохранения файла.
    """
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Template"

    # Заголовки — строго как в шаблоне Odoo
    ws.append(ODOO_HEADERS)

    invoice_num = data.get("invoice_number", "unknown")
    supplier = data.get("supplier") or {}
    inn = supplier.get("inn") or "x"
    items = data.get("items") or []

    for idx, item in enumerate(items, start=1):
        line_no = item.get("line_no") or idx
        qty = item.get("qty") or 0
        price = item.get("price") or 0
        amount = item.get("amount_w_vat") or 0

        sales_price = round(amount / qty, 2) if qty else 0

        parts = []
        if item.get("unit"):
            parts.append(f"Ед.: {item['unit']}")
        if item.get("vat_rate") is not None:
            parts.append(f"НДС: {item['vat_rate']}%")
        if qty:
            parts.append(f"Кол-во: {qty}")

        ws.append([
            f"inv_{inn}_{invoice_num}_{line_no}",  # External ID
            (item.get("name") or "").strip(),       # Name
            "Goods",                                 # Product Type
            item.get("article") or "",               # Internal Reference
            "",                                      # Barcode
            sales_price,                             # Sales Price
            price,                                   # Cost
            "",                                      # Weight
            "\n".join(parts),                        # Sales Description
        ])

    wb.save(output_path)
    logger.info(f"Odoo XLSX saved: {output_path}, rows: {len(items)}")
```

**Требования к коду:**
- Защита от `None` через `or` (не `if x is not None`)
- Ранний return не нужен (нет сложных ветвлений)
- Не вызывать LLM API, только трансформация данных
- Длина функции ≤ 50 строк

---

### ODOO-001.4 — Расширить `POST /convert` в `backend/app.py`
**Статус:** [x] Выполнено
**Файл:** `services/invoice-extractor/backend/app.py`

**Изменения:**

1. **Импорт** (строка ~21, после `from app.excel_builder import build_excel`):
   ```python
   from app.odoo_builder import build_odoo_xlsx
   ```

2. **Валидация output_mode** (строка ~150, после `output_mode = request.form.get(...)`):
   ```python
   VALID_OUTPUT_MODES = {"json", "xlsx", "both", "odoo_xlsx"}
   if output_mode not in VALID_OUTPUT_MODES:
       return jsonify({"error": f"Недопустимый output. Допустимые значения: {', '.join(sorted(VALID_OUTPUT_MODES))}"}), 400
   ```

3. **Docstring** `/convert` (строка ~126): добавить `odoo_xlsx` в список значений `output`

4. **Новый блок после `if output_mode == "xlsx":` (строка ~196)**:
   ```python
   if output_mode == "odoo_xlsx":
       odoo_path = OUTPUT_FOLDER / f"{job_id}_odoo.xlsx"
       logger.info(f"Building Odoo XLSX: {odoo_path}")
       build_odoo_xlsx(invoice_data, str(odoo_path))
       safe_filename = quote(f"odoo_{invoice_number}.xlsx", safe='')
       return send_file(
           str(odoo_path),
           mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
           as_attachment=True,
           download_name=safe_filename,
       ), 200, {**headers, "X-Output-Mode": "odoo_xlsx"}
   ```

**Порядок блоков в convert() после изменения:**
```
if output_mode == "json": ...
build_excel(...)
if output_mode == "xlsx": ...
if output_mode == "odoo_xlsx": ...
# both — возвращаем JSON + путь к файлу
```

---

### ODOO-001.5 — Тесты
**Статус:** [x] Выполнено
**Файл:** `services/invoice-extractor/backend/tests/test_odoo_builder.py`

**Список тестов:**

| Тест | Что проверяет |
|------|---------------|
| `test_build_odoo_xlsx_creates_file` | Файл создаётся по указанному пути |
| `test_build_odoo_xlsx_sheet_name` | Имя листа = "Template" |
| `test_build_odoo_xlsx_headers` | Строка 1: ровно 9 заголовков, точные имена |
| `test_build_odoo_xlsx_row_count` | Строк данных = len(items) |
| `test_build_odoo_xlsx_external_id_format` | External ID = `inv_{inn}_{invoice_num}_{line_no}` |
| `test_build_odoo_xlsx_sales_price_calculation` | `sales_price = amount_w_vat / qty` |
| `test_build_odoo_xlsx_zero_qty_protection` | qty=0 → sales_price=0, нет ZeroDivisionError |
| `test_build_odoo_xlsx_empty_items` | Пустой items → только строка заголовков |
| `test_build_odoo_xlsx_missing_optional_fields` | Нет article/unit/vat_rate → пустые ячейки, нет исключений |
| `test_build_odoo_xlsx_product_type_always_goods` | Product Type = "Goods" для всех строк |
| `test_convert_odoo_xlsx_endpoint` | POST /convert с output=odoo_xlsx → 200, mimetype=xlsx |
| `test_convert_invalid_output_mode` | POST /convert с output=invalid → 400 |

**Фикстура данных:**
```python
# conftest.py или в файле теста
SAMPLE_DATA = {
    "invoice_number": "INV-001",
    "supplier": {"inn": "1234567890", "name": "ООО Тест"},
    "items": [
        {
            "line_no": 1, "name": "Кабель ВВГнг 3x2.5",
            "article": "KBL-001", "unit": "м",
            "qty": 100, "price": 70.44,
            "vat_rate": 20, "vat_amount": 1408.8,
            "amount_w_vat": 8452.8, "discount": 0,
        }
    ],
}
```

**Интеграционный тест** (`test_convert_odoo_xlsx_endpoint`):
- Использовать мок `extract_invoice` → возвращает `SAMPLE_DATA`
- `POST /convert`, `output=odoo_xlsx`, PDF-заглушка
- Проверить: статус 200, `Content-Type: application/vnd.openxmlformats-...`, заголовок `X-Output-Mode: odoo_xlsx`

---

### ODOO-001.6 — Документация
**Статус:** [x] Выполнено
**Файлы:**
- `docs/changelog.md` — добавить запись о новом output режиме `odoo_xlsx`
- `docs/project.md` — обновить описание публичного API `/convert` (параметр `output`)
- `CLAUDE.md` — в разделе `### invoice-extractor` обновить список output-режимов

---

## Зависимости между задачами

```
ODOO-001.1 (сверить шаблон)
    └── ODOO-001.2 (финализировать маппинг)
            └── ODOO-001.3 (реализовать odoo_builder.py)
                    ├── ODOO-001.4 (расширить app.py)
                    └── ODOO-001.5 (тесты)
                                └── ODOO-001.6 (документация)
```

---

## Критерии приёмки

- [x] `pytest services/invoice-extractor/` — все тесты зелёные, включая новые (86/86)
- [ ] `ruff check services/invoice-extractor/` — ruff не установлен в окружении
- [x] `POST /convert` с `output=unknown` → 400 с понятным сообщением
- [ ] `curl -F "file=@test.pdf" -F "output=odoo_xlsx" http://localhost:5002/convert -o odoo.xlsx` — проверить вручную
- [ ] Скачанный `.xlsx` импортируется в Odoo без ручных правок заголовков
- [ ] Повторный импорт того же счёта обновляет записи, не создаёт дубли (за счёт External ID)

---

## Примечания

- `openpyxl` уже есть в `requirements.txt` — новых зависимостей не нужно
- Файл `odoo_{job_id}.xlsx` сохраняется в `outputs/` — нужно добавить очистку в `finally` (аналогично PDF)
- Заголовки Odoo матчит по точному имени строки — малейший пробел или регистр поломает импорт
