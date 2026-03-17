"""
@file: app.py
@description: Flask-бэкенд конвертера спецификаций PDF → Excel.
  Text-first pipeline с fallback на vision OCR (Anthropic / OpenRouter / OpenAI).
  Поддерживает параметры vision_only и provider из запроса (Advanced mode).
  Отправляет заголовки X-Vision-Fallback и X-Sheet-Names.
@dependencies: spec_utils.py, pdf_text_extractor.py, .env
@created: 2026-02-18
"""

import os
import re
import uuid
import time
from collections import Counter

import pdfplumber
from flask import Flask, request, send_file, jsonify, make_response
from flask_cors import CORS
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

from llm_client import call_vision_llm, pdf_to_images, parse_json_response

from spec_utils import SpecificationExcelBuilder
from pdf_text_extractor import has_text_layer, extract_table_from_text, normalize_table_to_9cols

# ──────────────────────────────────────────────────────────────────────────────
# Конфигурация
# ──────────────────────────────────────────────────────────────────────────────

load_dotenv()

import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

API_PROVIDER:      str | None = os.getenv('API_PROVIDER')
MODEL_NAME:        str | None = os.getenv('MODEL_NAME')
MAX_TOKENS:        int        = int(os.getenv('MAX_TOKENS', '16000'))
REQUEST_TIMEOUT:   int        = int(os.getenv('REQUEST_TIMEOUT_SEC', '120'))

def _get_api_key(provider: str | None) -> str | None:
    if provider == 'anthropic':
        return os.getenv('ANTHROPIC_API_KEY')
    if provider == 'openrouter':
        return os.getenv('OPENROUTER_API_KEY')
    if provider == 'openai':
        return os.getenv('OPENAI_API_KEY')
    return None

API_KEY = _get_api_key(API_PROVIDER)

if API_PROVIDER and API_KEY:
    logger.info("Конфигурация: %s / %s", API_PROVIDER, MODEL_NAME)
else:
    logger.warning("Переменные окружения не настроены (только text-режим). Задайте API_PROVIDER и ключ в .env")

# ──────────────────────────────────────────────────────────────────────────────
# Flask
# ──────────────────────────────────────────────────────────────────────────────

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024  # 50 MB
ALLOWED_ORIGINS = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "http://localhost:8080").split(",")]
CORS(app, origins=ALLOWED_ORIGINS)

_BASE_DIR     = os.path.dirname(__file__)
UPLOAD_FOLDER = os.path.join(_BASE_DIR, '..', 'uploads')
OUTPUT_FOLDER = os.path.join(_BASE_DIR, '..', 'output')
ALLOWED_EXTENSIONS = {'pdf'}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# ──────────────────────────────────────────────────────────────────────────────
# Vision prompts
# ──────────────────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """Ты — эксперт по чтению и извлечению данных из российских инженерных спецификаций (проектная документация ВК, ОВ, ЭО и т.д.).

Твоя задача — ТОЧНО прочитать таблицу спецификации с изображения и вернуть данные в JSON.
Качество изображения может быть низким — используй контекст и инженерную терминологию для ПРАВИЛЬНОГО прочтения.

СЛОВАРЬ ТЕРМИНОВ СПЕЦИФИКАЦИЙ ВК (используй для проверки):

Водопровод (В1, В2, В1-3):
- Водомерный узел УВ1, в т.ч.: (НЕ «ЧВ1», НЕ «Ду 15 м.ч.»)
- задвижка фланцевая с обрезиненным клином (НЕ «заглушка с обезжиренным ключом»)
- задвижка фланцевая с электроприводом (НЕ «с электропроводом»)
- фильтр для водомера муфтовый (НЕ «для бытового водопровода»)
- кран шаровой полнопроходный стальной с внутренней резьбой
- кран трёхходовой латунный для манометра (НЕ «натяжной»)
- манометр общего назначения
- счётчик холодной воды (ВСХНд-40)

Горячее водоснабжение (Т3, Т4):
- полотенцесушитель латунный (НЕ «подогреватель»)
- автоматический воздухоотводчик (НЕ «атмосферический»)

Пожарный водопровод:
- кран пожарный, в т.ч.:
- вентиль запорный пожарный с муфтой и цапкой из ковкого чугуна (НЕ «хабового»)
- головка цапковая напорная ГЦ-50 (НЕ «шарковая ГШ-50»)
- головка рукавная напорная ГР-50
- ствол ручной пожарный РС-50 dспр=16мм
- рукав напорный пожарный льняной

Трубы и фитинги:
- трубы полипропиленовые марки РN20 (Ду15мм, Ду20мм, Ду25мм)
- соединительные детали PPRC: (с учётом 15%) (угольники, тройники, муфты) (НЕ «фольгинки/фольники»)
- металл на крепление труб (НЕ «мелкий на крепление»)
- теплоизоляция магистральных труб трубками из вспененного полиэтилена Energoflex

Канализация (К1):
- трубы чугунные безраструбные, трубы канализационные полипропиленовые
- отвод, тройник, крестовина, заглушка, аэратор, трап
- противопожарная манжета (муфта) Огнеза-ПМ

Сантехника:
- умывальник керамический, унитаз керамический «Компакт»
- поливочный кран (смеситель настенный См-Ум-НВР) (НЕ «полубочный», НЕ «спецситель»)

Заводы/поставщики: ЛЗТА «Маршал», Valtec, Smart SML, Энергофлекс

ЧАСТЫЕ ОШИБКИ ЧТЕНИЯ СИМВОЛОВ:
- Кириллица У ↔ Ч: «УВ1» не «ЧВ1»
- Кириллица Ц ↔ Ш: «цапковая ГЦ-50» не «шарковая ГШ-50»
- Кириллица д ↔ л: «задвижка» не «заглушка» (в контексте фланцевой арматуры)
- Ф ↔ О: Ф = диаметр (Ф50, Ф15, Фу50)
- 0 ↔ О, 3 ↔ З: Ду40 не ДуЗО
- «в т.ч.:» не «м.ч.», не «б.т.ч.», не «D п.ч.»
- Масса через ЗАПЯТУЮ: «11,0» не «110», «0,156» не «0.156»
- Марки арматуры: «11с67пЦП.00.1», «30ч906бр», «11Б18бр», «15кч11р», «ФМФ Ф50»"""

EXTRACTION_PROMPT = """Извлеки ВСЕ данные из таблицы спецификации на изображении в JSON.

СТРУКТУРА ТАБЛИЦЫ (9 колонок, всегда в ЭТОМ логическом порядке):
1. Позиция (например: "В1-3", "Т3, Т4", "К1", "1.1", "-", или пустая "")
2. Наименование и техническая характеристика
3. Тип, марка, обозначение документа, опросного листа
4. Код оборудования/изделия/материала (или "Код продукции")
5. Завод-изготовитель (или "Поставщик")
6. Единица измерения (шт., компл., м, кг, м.п., м²/кг и т.д.)
7. Количество (число или диапазон)
8. Масса единицы, кг (или "Масса 1 ед., кг")
9. Примечание

ВАЖНО ПРО МАКЕТ СТРАНИЦЫ:
- Колонки на изображении могут идти в НЕСТАНДАРТНОМ порядке (например: 7 8 6 9 4 5 3 2 1).
- Номера колонок обычно указаны в нижней строке заголовка таблицы.
- ВСЕГДА переставляй данные в ПРАВИЛЬНЫЙ логический порядок (1-9), независимо от порядка на изображении.
- Таблица может быть повёрнута или зеркально отражена — это нормально для спецификаций.

ПРАВИЛА ИЗВЛЕЧЕНИЯ:
1. Первая строка rows = ЗАГОЛОВОК таблицы (названия колонок в правильном порядке 1-9).
2. Далее ВСЕ строки данных по порядку сверху вниз.
3. Пустые ячейки = "" (пустая строка).
4. Многострочный текст в одной ячейке → объединяй через пробел в одну строку.
5. "в т.ч.:" — далее идут компоненты (строки с тире "-" в начале наименования).
6. Числа с запятой (русский формат): "11,0" "0,156" "4,38" — сохраняй КАК ЕСТЬ.
7. Сохраняй ВСЕ спецсимволы: Ф, Ду, ², ³, °, ±, ×.
8. ЗАГОЛОВОК секции (например "Трубопровод горячего водоснабжения") — это строка данных с позицией секции (Т3, Т4 и т.д.) или пустой позицией.
9. Если на странице НЕСКОЛЬКО таблиц или секций — включи ВСЕ строки в один массив rows.
10. НЕ пропускай строки! Каждая строка таблицы должна быть в результате.
11. Игнорируй рамку чертежа, штамп, подписи, номера листов — извлекай ТОЛЬКО данные таблицы.

ФОРМАТ ОТВЕТА (ТОЛЬКО JSON, без ```json обёртки):
{
  "sheet_name": "краткое название секции (В1-3, Т3-Т4, К1 и т.д.)",
  "rows": [
    ["Позиция", "Наименование и техническая характеристика", "Тип, марка, обозначение документа, опросного листа", "Код оборудования, изделия, материала", "Завод-изготовитель", "Единица измерения", "Количество", "Масса единицы, кг", "Примечание"],
    ["...", "...", "...", "...", "...", "...", "...", "...", "..."]
  ]
}"""

# ──────────────────────────────────────────────────────────────────────────────
# Spec-specific response normalization
# ──────────────────────────────────────────────────────────────────────────────

def _parse_spec_response(response_text: str) -> dict:
    """Парсит JSON-ответ LLM и нормализует строки таблицы до 9 колонок."""
    data = parse_json_response(response_text)
    rows = data.get('rows', [])
    if rows:
        target_cols = max(max(len(r) for r in rows), 9)
        for i, row in enumerate(rows):
            if len(row) < target_cols:
                rows[i] = row + [''] * (target_cols - len(row))
            elif len(row) > target_cols:
                rows[i] = row[:target_cols]
    return {'sheet_name': data.get('sheet_name', 'Спецификация'), 'rows': rows}

# ──────────────────────────────────────────────────────────────────────────────
# Excel builder
# ──────────────────────────────────────────────────────────────────────────────

def _create_excel(pages_data: list, output_path: str) -> list[str]:
    """Создаёт Excel из данных страниц. Возвращает список имён листов."""
    builder   = SpecificationExcelBuilder(output_path)
    raw_names = []

    for page_data in pages_data:
        name = page_data.get('sheet_name', 'Спецификация')
        name = re.sub(r'\s*стр\.?\s*\d*$', '', name).strip()
        raw_names.append(name)

    name_counts = Counter(raw_names)
    sheet_names = []

    for idx, page_data in enumerate(pages_data):
        rows = page_data.get('rows', [])
        if not rows:
            continue

        base_name = raw_names[idx]
        page_num  = page_data.get('page_num', idx + 1)

        sheet_name = (
            f'{base_name} стр.{page_num}' if name_counts[base_name] > 1 else base_name
        )
        if len(sheet_name) > 31:
            sheet_name = sheet_name[:28] + f'..{page_num}'

        # Убедимся что первая строка — заголовок
        if rows and not all(isinstance(c, str) for c in rows[0]):
            rows.insert(0, [
                'Позиция', 'Наименование и техническая характеристика',
                'Тип, марка, обозначение документа, опросного листа',
                'Код оборудования, изделия, материала', 'Завод-изготовитель',
                'Единица измерения', 'Количество', 'Масса единицы, кг', 'Примечание',
            ])

        # Фильтрация мусора
        filtered = [
            row for row in rows
            if not (
                all(v in ('1','2','3','4','5','6','7','8','9','') for v in [str(c).strip() for c in row])
                and any(v in ('1','2','3','4','5','6','7','8','9') for v in [str(c).strip() for c in row])
            ) and any(str(c).strip() for c in row)
        ]

        logger.debug("Лист '%s': %d строк", sheet_name, len(filtered))
        builder.create_sheet(sheet_name, filtered)
        sheet_names.append(sheet_name)

    if sheet_names:
        builder.save()

    return sheet_names

# ──────────────────────────────────────────────────────────────────────────────
# Core pipeline
# ──────────────────────────────────────────────────────────────────────────────

def process_pdf(pdf_path: str, provider: str | None = None, api_key: str | None = None,
                model: str | None = None, force_vision: bool = False) -> tuple[list, bool]:
    """Text-first pipeline с optional vision fallback.

    Returns:
        (pages_data, vision_was_used)
    """
    eff_provider = provider or API_PROVIDER
    eff_key      = api_key  or API_KEY
    eff_model    = model    or MODEL_NAME

    pages_data       = []
    vision_was_used  = False
    images: list | None = None

    logger.debug("Проверка текстового слоя...")
    text_flags = has_text_layer(pdf_path)
    logger.debug("Страниц с текстом: %d/%d", sum(text_flags), len(text_flags))

    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages):
            page_num = i + 1

            if not force_vision and text_flags[i]:
                logger.debug("Страница %d: текстовый режим", page_num)
                try:
                    raw_rows, pdf_header = extract_table_from_text(page)
                    if raw_rows and len(raw_rows) > 1:
                        page_data = normalize_table_to_9cols(raw_rows, page_num, pdf_header)
                        page_data['page_num'] = page_num
                        pages_data.append(page_data)
                        logger.info("Страница %d: текст — '%s', %d строк", page_num, page_data['sheet_name'], len(page_data['rows']))
                        continue
                    logger.warning("Страница %d: пустая таблица, переход на vision-режим", page_num)
                except Exception as e:
                    logger.warning("Страница %d: ошибка текстового режима (%s), переход на vision-режим", page_num, e)

            # Vision fallback / force_vision
            if not eff_provider or not eff_key:
                logger.warning("Страница %d: vision недоступен (API не настроен)", page_num)
                continue

            logger.debug("Страница %d: vision-режим", page_num)
            if images is None:
                logger.debug("Генерация изображений...")
                images = pdf_to_images(pdf_path)

            image_data, _media_type = images[i]
            success = False

            for attempt in range(3):
                wait_sec = 3
                try:
                    raw_text = call_vision_llm(
                        [image_data], EXTRACTION_PROMPT, eff_provider,
                        system_prompt=SYSTEM_PROMPT,
                        api_key=eff_key, model=eff_model,
                        max_tokens=MAX_TOKENS, timeout=REQUEST_TIMEOUT, temperature=0,
                    )
                    page_data = _parse_spec_response(raw_text)
                    if page_data and page_data.get('rows') and len(page_data['rows']) > 1:
                        page_data['page_num'] = page_num
                        pages_data.append(page_data)
                        logger.info("Страница %d: vision — '%s', %d строк", page_num, page_data.get('sheet_name', '?'), len(page_data['rows']))
                        vision_was_used = True
                        success = True
                        break
                    logger.warning("Страница %d: пустой результат (попытка %d/3)", page_num, attempt + 1)
                except Exception as e:
                    err = str(e).lower()
                    is_network = any(k in err for k in ('resolve', 'connection', 'timeout', 'gaierror'))
                    if is_network:
                        wait_sec = 5 * (attempt + 1)
                        logger.warning("Страница %d: сетевая ошибка (попытка %d/3), жду %dс: %s", page_num, attempt + 1, wait_sec, str(e)[:120])
                    else:
                        logger.error("Страница %d: ошибка (попытка %d/3): %s", page_num, attempt + 1, str(e)[:200])
                if attempt < 2:
                    time.sleep(wait_sec)

            if not success:
                logger.error("Страница %d пропущена после 3 попыток", page_num)

    return pages_data, vision_was_used

# ──────────────────────────────────────────────────────────────────────────────
# Routes
# ──────────────────────────────────────────────────────────────────────────────

def _allowed_file(filename: str) -> bool:
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def _safe_filename(original: str) -> str:
    """UUID-префикс + безопасное имя. Сохраняет расширение, устойчив к кириллице."""
    ext = original.rsplit(".", 1)[-1].lower() if "." in original else ""
    safe = secure_filename(original)
    base = safe.rsplit(".", 1)[0] if safe and safe != f".{ext}" else "file"
    return f"{uuid.uuid4().hex[:12]}_{base}.{ext}"


def _validate_pdf(file_storage) -> tuple[bool, str | None]:
    """Проверяет, что загруженный файл действительно PDF.

    Проверяет расширение и magic bytes (%PDF-).
    """
    filename = file_storage.filename or ""
    if not filename.lower().endswith(".pdf"):
        return False, "Только PDF файлы"
    header = file_storage.read(8)
    file_storage.seek(0)
    if not header.startswith(b"%PDF-"):
        return False, "Файл не является настоящим PDF"
    try:
        import magic
        mime = magic.from_buffer(header, mime=True)
        if mime != "application/pdf":
            return False, f"Неверный MIME-тип: {mime}"
    except ImportError:
        pass
    return True, None


@app.route('/convert', methods=['POST'])
def convert_pdf():
    """POST /convert — конвертация PDF → Excel.

    Form fields:
        file         — PDF файл (обязательный)
        vision_only  — 'true' → принудительный vision-режим (Advanced mode)
        provider     — переопределить провайдера ('anthropic'|'openrouter'|'openai')
    """
    if 'file' not in request.files:
        return jsonify({'error': 'Файл не найден', 'code': 'NO_FILE'}), 400

    f = request.files['file']
    if not f.filename or not _allowed_file(f.filename):
        return jsonify({'error': 'Только PDF', 'code': 'INVALID_TYPE'}), 400

    valid, err = _validate_pdf(f)
    if not valid:
        return jsonify({'error': err, 'code': 'INVALID_FILE'}), 400

    vision_only   = request.form.get('vision_only', '').lower() == 'true'
    req_provider  = request.form.get('provider') or None
    req_api_key   = _get_api_key(req_provider) if req_provider else None
    req_model     = MODEL_NAME  # модель берётся из .env; провайдер может быть переопределён

    pdf_path = None
    original_name = f.filename or "file.pdf"
    try:
        filename = _safe_filename(original_name)
        pdf_path = os.path.join(UPLOAD_FOLDER, filename)
        f.save(pdf_path)

        eff_provider = req_provider or API_PROVIDER
        eff_key      = req_api_key  or API_KEY
        logger.info("Обработка файла: %s", original_name)
        if eff_provider and eff_key:
            logger.info("Vision: %s/%s%s", eff_provider, req_model, "  [force]" if vision_only else "")
        else:
            logger.warning("Vision недоступен (API не настроен) — только text-режим")

        pages_data, vision_was_used = process_pdf(
            pdf_path,
            provider=req_provider,
            api_key=req_api_key,
            force_vision=vision_only,
        )

        if not pages_data:
            return jsonify({'error': 'Нет данных для Excel', 'code': 'EMPTY_RESULT'}), 500

        logger.info("Создание Excel...")
        output_filename = filename.rsplit('.', 1)[0] + '.xlsx'
        output_path     = os.path.join(OUTPUT_FOLDER, output_filename)
        download_name   = original_name.rsplit('.', 1)[0] + '.xlsx'

        sheet_names = _create_excel(pages_data, output_path)

        if not sheet_names:
            return jsonify({'error': 'Ошибка создания Excel', 'code': 'EXCEL_ERROR'}), 500

        logger.info("Готово: %s", output_filename)

        response = make_response(send_file(
            output_path,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=download_name,
        ))
        response.headers['X-Vision-Fallback'] = 'true' if vision_was_used else 'false'
        # HTTP-заголовки должны быть ASCII/latin-1; кодируем кириллицу через URL-encoding
        from urllib.parse import quote
        response.headers['X-Sheet-Names'] = quote(','.join(sheet_names), safe=',')
        return response

    except Exception as e:
        logger.exception("Ошибка обработки: %s", e)
        return jsonify({'error': str(e), 'code': 'INTERNAL_ERROR'}), 500
    finally:
        if pdf_path and os.path.exists(pdf_path):
            try:
                os.remove(pdf_path)
            except OSError:
                pass


@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        'status':     'ok',
        'service':    'spec-converterv2',
        'version':    '2.0.0',
        'provider':   API_PROVIDER,
        'model':      MODEL_NAME,
        'configured': API_KEY is not None,
    })


if __name__ == '__main__':
    logger.info("Конвертер спецификаций (services/spec-converterv2)")
    if API_PROVIDER and API_KEY:
        logger.info("Провайдер: %s, Модель: %s", API_PROVIDER, MODEL_NAME)
    else:
        logger.error("API не настроен! Задайте переменные в .env")
    app.run(debug=True, host='0.0.0.0', port=5001)
