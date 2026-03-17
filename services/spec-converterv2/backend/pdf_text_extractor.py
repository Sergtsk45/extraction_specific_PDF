"""
Модуль для извлечения таблиц спецификаций из текстового слоя PDF.

Используется как основной метод (text-first) с fallback на vision OCR
для PDF без текстового слоя или со сканами.

Ключевая идея: строка нумерации колонок (1 2 3 4 5 6 7 8 9) в PDF-таблице
используется как карта маппинга сырых колонок → логические 9 колонок спецификации.
"""

import pdfplumber
import re
from typing import List, Dict, Optional


# Ключевые слова для проверки валидности текстового слоя
SPEC_KEYWORDS = [
    "Позиция", "Наименование", "Единица", "шт", "компл", "Ду", "Ф",
    "задвижка", "кран", "труба", "арматура", "Завод", "измерения",
    "Количество", "Масса", "Тип", "марка"
]

# Стандартный заголовок 9-колоночной спецификации
STANDARD_HEADER = [
    "Позиция",
    "Наименование и техническая характеристика",
    "Тип, марка, обозначение документа, опросного листа",
    "Код оборудования, изделия, материала",
    "Завод-изготовитель",
    "Единица измерения",
    "Количество",
    "Масса единицы, кг",
    "Примечание"
]

# Ключевые слова штампа/рамки (нормальные + битая кодировка CP1251 как Latin1)
STAMP_KEYWORDS = [
    "изм.", "подп.", "формат", "инв.", "взам.", "листов",
    "разработал", "проверил", "норм. контр", "гип", "стадия",
    "утвердил", "н. контр",
    # битая кодировка
    "èçì", "ïîäï", "ôîðìàò", "èíâ", "âçàì", "ëèñò",
    "ðàçðàáîòàë", "ïðîâåðèë", "íîðì", "ãèï", "ñòàäèÿ",
    "óòâåðäèë",
    # названия проектов/документов в штампе
    "2273-1.1-", "ìíîãîêâàðòèðíûé", "ïðèñòðîåííûå",
    "многоквартирный", "пристроенные помещения",
    # вертикальные надписи
    "№ док", "разраб.", "н. контр.", "подп. и дата",
]


def fix_encoding(text: str) -> str:
    """
    Исправляет битую кодировку CP1251→UTF8.

    PDF иногда содержит текст, где CP1251 байты были интерпретированы как Latin1.
    Метод: пробуем encode обратно в latin1, затем decode как cp1251.

    Проверяем успешность: после decode не должно быть символов 0xC0-0xFF,
    и результат должен содержать хотя бы 1 кириллическую букву.
    """
    if not text or not text.strip():
        return text

    try:
        raw_bytes = text.encode('latin1')
        decoded = raw_bytes.decode('cp1251')
        # Проверяем: не осталось ли артефактов 0xC0-0xFF
        remaining_artifacts = sum(1 for c in decoded if '\u00C0' <= c <= '\u00FF')
        # Результат должен содержать кириллицу
        cyrillic_count = sum(1 for c in decoded if '\u0400' <= c <= '\u04FF')
        if cyrillic_count > 0 and remaining_artifacts == 0:
            return decoded
    except (UnicodeEncodeError, UnicodeDecodeError):
        pass

    return text


def needs_encoding_fix(text: str) -> bool:
    """Проверяет, нужна ли перекодировка (содержит ли текст характерные latin1-артефакты)."""
    if not text:
        return False
    # Характерные символы CP1251-как-Latin1: диапазон 0xC0-0xFF (À-ÿ)
    suspect_chars = sum(1 for c in text if '\u00C0' <= c <= '\u00FF')
    # Достаточно хотя бы одного подозрительного символа
    return suspect_chars >= 1


def fix_row_encoding(row: List[str]) -> List[str]:
    """Применяет fix_encoding к каждой ячейке строки, если нужно."""
    result = []
    for cell in row:
        if needs_encoding_fix(cell):
            result.append(fix_encoding(cell))
        else:
            result.append(cell)
    return result


def has_text_layer(pdf_path: str) -> List[bool]:
    """
    Проверяет, есть ли на каждой странице PDF валидный текстовый слой.

    Критерии: >= 200 символов + хотя бы одно ключевое слово.
    """
    text_flags = []

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""

            if len(text) < 200:
                text_flags.append(False)
                continue

            has_keyword = any(kw in text for kw in SPEC_KEYWORDS)
            text_flags.append(has_keyword)

    return text_flags


def find_column_mapping(table: List[List]) -> Optional[Dict[int, int]]:
    """
    Находит строку нумерации колонок (1 2 3 4 5 6 7 8 9) и строит маппинг:
    raw_col_index → logical_col_number (1-9).

    Строка нумерации — это строка, где непустые ячейки содержат ровно цифры 1-9.
    """
    for row_idx, row in enumerate(table[:5]):  # ищем в первых 5 строках
        if row is None:
            continue

        # Собираем непустые ячейки
        non_empty = {}
        for col_idx, cell in enumerate(row):
            if cell is not None and str(cell).strip() in ('1','2','3','4','5','6','7','8','9'):
                non_empty[col_idx] = int(str(cell).strip())

        # Если нашли 8-9 цифр — это строка нумерации
        if len(non_empty) >= 8:
            return non_empty

    return None


def extract_table_from_text(page) -> tuple:
    """
    Извлекает таблицу спецификации из текстового слоя страницы PDF.

    Алгоритм:
    1. Извлечь все таблицы через pdfplumber (стратегия: lines)
    2. Взять самую большую
    3. Найти строку нумерации (1-9) → определить маппинг колонок
    4. Применить маппинг: из 16-22 сырых колонок → 9 логических
    5. Отфильтровать штамп, пустые строки, нумерацию
    6. Исправить битую кодировку

    Returns:
        (rows, header) — строки данных и заголовок из PDF (или None)
    """
    table_settings = {
        "vertical_strategy": "lines",
        "horizontal_strategy": "lines",
        "snap_tolerance": 5,
        "join_tolerance": 5,
        "text_tolerance": 3,
    }

    tables = page.extract_tables(table_settings)
    if not tables:
        return []

    largest_table = max(tables, key=lambda t: sum(len(r) for r in t))

    # Находим маппинг колонок по строке нумерации
    col_map = find_column_mapping(largest_table)

    if not col_map:
        # Fix 3: Fallback 1 — маппинг по строке-заголовку таблицы
        header_map = _find_header_mapping(largest_table)
        if header_map:
            col_map = {raw_idx: logical_num for logical_num, raw_idx in header_map.items()}
            # Продолжаем основной алгоритм с этим маппингом
        else:
            # Fallback 2: старый fallback (крайний случай)
            return _extract_fallback(largest_table), None

    # Строим маппинг: logical_col (1-9) → raw_col_index
    logical_to_raw = {}
    for raw_idx, logical_num in col_map.items():
        logical_to_raw[logical_num] = raw_idx

    # Извлекаем заголовок из PDF (строка 0 — заголовок с названиями колонок)
    pdf_header = _extract_pdf_header(largest_table, logical_to_raw)

    # Применяем маппинг к каждой строке
    filtered_rows = []

    for row_idx, row in enumerate(largest_table):
        if row is None:
            continue

        # Маппим 9 логических колонок
        mapped_row = []
        for logical_num in range(1, 10):
            raw_idx = logical_to_raw.get(logical_num)
            if raw_idx is not None and raw_idx < len(row):
                cell = row[raw_idx]
                val = str(cell).strip() if cell is not None else ""
                # Убираем переносы строк внутри ячейки (склеиваем)
                val = " ".join(val.split('\n')).strip()
                # Fix 1: склейка разрывов подстрочных индексов (DУ, РУ, DН, РН)
                val = re.sub(r'\bD\s+У\b', 'DУ', val)
                val = re.sub(r'\bР\s+У\b', 'РУ', val)
                val = re.sub(r'\bD\s+Н\b', 'DН', val)
                val = re.sub(r'\bР\s+Н\b', 'РН', val)
                mapped_row.append(val)
            else:
                mapped_row.append("")
        
        # Фильтры
        row_text = " ".join(mapped_row).lower()

        # Фильтр: строка заголовка таблицы (Позиция, Наименование...)
        if any(kw in row_text for kw in ["позиция", "наименование и техническая",
                                          "я и ц и з о п", "поз."]):
            continue

        # Фильтр: строка нумерации (1 2 3 4 5 6 7 8 9)
        if all(c in ('1','2','3','4','5','6','7','8','9','') for c in mapped_row):
            if sum(1 for c in mapped_row if c in ('1','2','3','4','5','6','7','8','9')) >= 5:
                continue

        # Фильтр: штамп/рамка
        if _is_stamp_row(row_text, mapped_row):
            continue

        # Фильтр: полностью пустая строка
        if all(c == '' for c in mapped_row):
            continue

        # Фильтр: вертикальные надписи (содержат \n между каждым символом)
        if _is_vertical_text(mapped_row):
            continue

        # Исправляем кодировку
        mapped_row = fix_row_encoding(mapped_row)

        # Пост-обработка: если данные слиплись (позиция+текст в одной ячейке)
        mapped_row = _fix_merged_cells(mapped_row)

        # Нормализация позиции: "-" → "" (тире = нет позиции)
        if mapped_row[0] == "-":
            mapped_row[0] = ""

        filtered_rows.append(mapped_row)

    # Fix 4: склейка строк-продолжений
    filtered_rows = _merge_continuation_rows(filtered_rows)

    return filtered_rows, pdf_header


def _fix_merged_cells(row: List[str]) -> List[str]:
    """
    Исправляет строки, где данные слиплись.

    Пример: col1="3 Трап вертикальный..." (позиция+наименование+тип)
    Нужно разделить: col1="3", col2="Трап вертикальный...", col3="ГОСТ..."

    Также: col4="шт 4" → col6="шт", col7="4"
    """
    # Fix 2: извлечение позиции из наименования ("54. Биметаллический..." → col[0]="54.")
    if not row[0].strip() and row[1].strip():
        match = re.match(r'^(\d+(?:\.\d+)?\.?)\s+(.+)$', row[1].strip(), re.DOTALL)
        if match:
            candidate_pos = match.group(1)
            if re.match(r'^\d{1,3}(?:\.\d{1,2})?\.?$', candidate_pos):
                row[0] = candidate_pos
                row[1] = match.group(2).strip()

    # Проверка: позиция (col1) содержит пробел и длинный текст → слипание
    pos = row[0]
    if pos and ' ' in pos and len(pos) > 5:
        # Пытаемся отделить число-позицию от текста
        match = re.match(r'^(\d+(?:\.\d+)?)\s+(.+)$', pos, re.DOTALL)
        if match:
            new_pos = match.group(1)
            rest = match.group(2)
            # Если col2 пустая — переносим текст туда
            if not row[1]:
                row[0] = new_pos
                row[1] = rest
                # Если в rest есть ГОСТ или SML — отделяем
                gost_match = re.search(r'\s+(ГОСТ\s+[\d-]+|SML\s+\d+|ТУ\s+[\d.-]+)', rest)
                if gost_match:
                    row[1] = rest[:gost_match.start()].strip()
                    if not row[2]:
                        row[2] = gost_match.group(1).strip()

    # Проверка: col4 (код) содержит "шт 4" → unit+qty
    code = row[3]
    if code and re.match(r'^(шт|компл|м|кг|м\.п\.|м2|м2/кг|м/м)\s+(\d+)', code):
        match = re.match(r'^(\S+)\s+(\d+(?:[,\.]\d+)?)', code)
        if match:
            if not row[5]:
                row[5] = match.group(1)
            if not row[6]:
                row[6] = match.group(2)
            row[3] = ""

    # Склейка col3 (тип/марка) + col4 (код): если оба непустые и col4 - чистое число
    if row[2] and row[3] and re.match(r'^\d+$', row[3]):
        row[2] = row[2] + " " + row[3]
        row[3] = ""

    # Исправление "м/м3" → "м/м" + qty="3" (кол-во влипло в единицу)
    unit_qty_match = re.match(r'^(м/м|м\.п\./м|м²/кг|м2/кг)(\d+(?:[,\.]\d+)?)$', row[5])
    if unit_qty_match and not row[6]:
        row[5] = unit_qty_match.group(1)
        row[6] = unit_qty_match.group(2)

    # Очистка лишних пробелов в значениях
    row = [re.sub(r'\s+', ' ', cell).strip() for cell in row]

    # Исправление "ЛЗТА \" Маршал\"" → "ЛЗТА \"Маршал\""
    for i, cell in enumerate(row):
        row[i] = cell.replace('" ', '"').replace(' "', '"')
        if row[i].startswith('"') and row[i].endswith('"'):
            pass  # OK
        # ЛЗТА "Маршал" — убираем лишние пробелы вокруг кавычек
        row[i] = re.sub(r'"\s+', '"', row[i])
        row[i] = re.sub(r'\s+"', '"', row[i])

    return row


def _extract_pdf_header(table: List[List], logical_to_raw: Dict[int, int]) -> Optional[List[str]]:
    """
    Извлекает заголовок таблицы из PDF (первая строка — названия колонок).
    Возвращает None если заголовок стандартный.
    """
    if not table or len(table) < 1:
        return None

    header_row = table[0]
    if header_row is None:
        return None

    mapped_header = []
    for logical_num in range(1, 10):
        raw_idx = logical_to_raw.get(logical_num)
        if raw_idx is not None and raw_idx < len(header_row):
            cell = header_row[raw_idx]
            val = str(cell).strip() if cell is not None else ""
            val = " ".join(val.split('\n')).strip()
            # Исправляем кодировку заголовков
            if needs_encoding_fix(val):
                val = fix_encoding(val)
            mapped_header.append(val)
        else:
            mapped_header.append("")

    # Проверяем: похож ли заголовок на реальный заголовок таблицы
    header_keywords = ["позиц", "наименование", "единиц", "количество", "масса",
                       "тип", "марка", "код", "завод", "поставщик", "примечан",
                       "поз.", "кол-во", "еди-"]
    header_text = " ".join(mapped_header).lower()
    if not any(kw in header_text for kw in header_keywords):
        return None

    # Исправляем вертикальную надпись "я и ц и з о П" → "Позиция"
    if mapped_header[0] and ("я и ц" in mapped_header[0].lower() or "з о п" in mapped_header[0].lower()):
        mapped_header[0] = "Позиция"

    # Исправляем артефакты в заголовках
    for i, val in enumerate(mapped_header):
        # "оюозначение" (битый OCR) → "обозначение"
        val = val.replace("оюозначение", "обозначение")
        # Убираем дефисы-переносы: "измере- ния" → "измерения"
        val = re.sub(r'-\s+', '', val)
        # "Коли чество" → "Количество"
        val = re.sub(r'\s+', ' ', val).strip()
        mapped_header[i] = val

    return mapped_header


def _is_stamp_row(row_text: str, mapped_row: List[str]) -> bool:
    """Проверяет, является ли строка частью штампа/рамки."""
    # Проверяем по ключевым словам штампа
    for kw in STAMP_KEYWORDS:
        if kw in row_text:
            return True

    # Проверяем каждую ячейку отдельно (штамп может быть в одной ячейке)
    for cell in mapped_row:
        cell_lower = cell.lower().strip()
        for kw in STAMP_KEYWORDS:
            if kw in cell_lower:
                return True

    return False


def _is_vertical_text(row: List[str]) -> bool:
    """
    Обнаруживает вертикальные надписи типа "№\\nв.\\nн\\nи\\nм.\\nа\\nз\\nВ".
    Такие надписи содержат много \\n и мало букв.
    """
    for cell in row:
        if '\n' in cell:
            parts = cell.split('\n')
            # Вертикальная надпись: много коротких частей
            if len(parts) >= 4 and all(len(p.strip()) <= 3 for p in parts):
                return True
    return False


def _find_header_mapping(table: List[List]) -> Optional[Dict[int, int]]:
    """
    Fallback-маппинг: ищет строку-заголовок таблицы по ключевым словам
    и строит маппинг logical_col (1-9) → raw_col_idx.

    Используется когда строка-нумератор (1 2 3 ... 9) не найдена.
    Если нашли >= 5 логических колонок — считаем маппинг достаточным.
    """
    HEADER_PATTERNS = {
        1: ["позиция", "поз."],
        2: ["наименование"],
        3: ["тип", "марка", "обозначение"],
        4: ["код"],
        5: ["завод", "изготовитель", "поставщик"],
        6: ["единиц", "ед.", "измер"],
        7: ["количеств", "кол-во", "кол."],
        8: ["масса"],
        9: ["примечан"],
    }

    for row in table[:5]:
        if row is None:
            continue

        row_texts = []
        for cell in row:
            val = str(cell).strip().lower() if cell else ""
            if needs_encoding_fix(val):
                val = fix_encoding(val).lower()
            row_texts.append(val)

        matches: Dict[int, int] = {}
        for col_idx, text in enumerate(row_texts):
            if not text:
                continue
            for logical_num, keywords in HEADER_PATTERNS.items():
                if logical_num in matches:
                    continue
                if any(kw in text for kw in keywords):
                    matches[logical_num] = col_idx
                    break

        if len(matches) >= 5:
            return matches

    return None


def _merge_continuation_rows(rows: List[List[str]]) -> List[List[str]]:
    """
    Склеивает строки-продолжения с предыдущей строкой.

    Строка считается продолжением если:
    - Позиция (col[0]) пуста
    - Только 1-2 колонки заполнены
    - Нет числовых данных в полях ед.изм/кол-во/масса (col 5-7)
    - Текст не начинается с "-" (не подпозиция)
    """
    if len(rows) < 2:
        return rows

    merged = [rows[0]]

    for row in rows[1:]:
        pos = row[0].strip()
        filled_cols = [(i, c) for i, c in enumerate(row) if c.strip()]

        has_position = bool(re.match(r'^\d+\.?', pos))
        starts_with_dash = row[1].strip().startswith('-') if len(row) > 1 and row[1].strip() else False
        has_numeric_data = any(row[i].strip() for i in [5, 6, 7] if i < len(row))

        is_continuation = (
            not pos
            and not has_position
            and not starts_with_dash
            and not has_numeric_data
            and len(filled_cols) <= 2
            and len(merged) > 0
        )

        if is_continuation:
            prev = merged[-1]
            for i, cell in enumerate(row):
                if cell.strip():
                    if i < len(prev):
                        if prev[i].strip():
                            prev[i] = prev[i].rstrip() + " " + cell.strip()
                        else:
                            prev[i] = cell.strip()
        else:
            merged.append(row)

    return merged


def _extract_fallback(table: List[List]) -> List[List[str]]:
    """
    Fallback: когда строка нумерации не найдена.
    Удаляем пустые (None) колонки и берём первые 9 непустых.
    """
    none_cols = _find_always_none_columns(table)

    filtered_rows = []
    for row in table:
        if row is None:
            continue
        clean = []
        for i, cell in enumerate(row):
            if i in none_cols:
                continue
            clean.append(str(cell).strip() if cell is not None else "")

        row_text = " ".join(clean).lower()
        if _is_stamp_row(row_text, clean):
            continue
        if all(c == '' for c in clean):
            continue

        # Подгоняем до 9 колонок
        if len(clean) > 9:
            clean = clean[:9]
        elif len(clean) < 9:
            clean = clean + [''] * (9 - len(clean))

        clean = fix_row_encoding(clean)
        filtered_rows.append(clean)

    return filtered_rows


def _find_always_none_columns(table: List[List]) -> set:
    """Находит колонки, которые None во всех строках."""
    if not table:
        return set()
    max_cols = max(len(r) for r in table if r)
    none_counts = [0] * max_cols
    row_count = 0
    for row in table:
        if row is None:
            continue
        row_count += 1
        for i in range(min(len(row), max_cols)):
            if row[i] is None:
                none_counts[i] += 1
    if row_count == 0:
        return set()
    return {i for i, cnt in enumerate(none_counts) if cnt >= row_count * 0.95}


def normalize_table_to_9cols(raw_rows: List[List[str]], page_num: int = 1,
                              page_header: Optional[List[str]] = None) -> Dict:
    """
    Обёртка: определяет sheet_name, добавляет заголовок, очищает данные.

    Args:
        raw_rows: строки данных после extract_table_from_text
        page_num: номер страницы
        page_header: заголовок из PDF (если None — используется стандартный)
    """
    if not raw_rows:
        return {"sheet_name": f"Спецификация стр.{page_num}", "rows": []}

    sheet_name = detect_sheet_name(raw_rows, page_num)

    # Используем заголовок из PDF если есть, иначе стандартный
    header = page_header if page_header else STANDARD_HEADER
    rows_with_header = [header] + raw_rows

    # Очищаем: убираем пустые хвосты
    clean_rows = []
    for row in rows_with_header:
        if all(cell.strip() == '' for cell in row):
            continue
        clean_rows.append(row)

    return {
        "sheet_name": sheet_name,
        "rows": clean_rows
    }


def detect_sheet_name(rows: List[List[str]], page_num: int) -> str:
    """
    Определяет название листа из содержимого таблицы.
    Ищет коды систем: В1-3, Т3, Т4, К1 и т.д.
    """
    system_patterns = [
        r'\b([ВТК]\d+(?:-\d+)?(?:,\s*[ВТК]\d+)*)\b',
        r'[Вв]одопровод\s+([Вв]\d+)',
        r'[Кк]анализация\s+([Кк]\d+)',
        r'водоснабжение\s+([Тт]\d+)',
    ]

    for row in rows[:5]:
        row_text = " ".join(row)
        for pattern in system_patterns:
            match = re.search(pattern, row_text)
            if match:
                return match.group(1)

    return f"Спецификация стр.{page_num}"


def detect_encoding_quality(text: str) -> bool:
    """Проверяет, не битый ли текст."""
    if not text:
        return False
    allowed = set('абвгдеёжзийклмнопрстуфхцчшщъыьэюяАБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ')
    allowed.update('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ')
    allowed.update('0123456789.,;:!?()[]{}/"\'`-–—+=*&%$#@№ \n\r\t')
    allowed.update('°²³×÷≈≤≥±ФΦ')
    strange = sum(1 for c in text if c not in allowed)
    return strange / len(text) < 0.30
