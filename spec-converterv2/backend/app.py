from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
import os
import fitz
import base64
import json
import re
from werkzeug.utils import secure_filename
from spec_utils import SpecificationExcelBuilder, SpecificationDataExtractor
from pdf_text_extractor import has_text_layer, extract_table_from_text, normalize_table_to_9cols
import pdfplumber

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = '../uploads'
OUTPUT_FOLDER = '../output'
ALLOWED_EXTENSIONS = {'pdf'}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# Загружаем конфигурацию
try:
    from config import API_PROVIDER, MODEL_NAME, MAX_TOKENS
    
    if API_PROVIDER == 'anthropic':
        from config import ANTHROPIC_API_KEY as API_KEY
    elif API_PROVIDER == 'openrouter':
        from config import OPENROUTER_API_KEY as API_KEY
    elif API_PROVIDER == 'openai':
        from config import OPENAI_API_KEY as API_KEY
    else:
        raise ValueError(f"Неизвестный провайдер: {API_PROVIDER}")
    
    print(f"✅ Конфигурация: {API_PROVIDER} / {MODEL_NAME}")
    
except ImportError:
    print("⚠️  config.py не найден!")
    API_PROVIDER = None
    API_KEY = None
    MODEL_NAME = None
    MAX_TOKENS = 4000


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def pdf_to_images(pdf_path):
    """Конвертирует PDF в изображения высокого разрешения (~288 DPI).
    
    Использует 4x zoom для максимальной чёткости мелкого шрифта.
    Если PNG > 4MB — пересохраняет как JPEG quality=90 для уменьшения размера.
    """
    from io import BytesIO
    
    doc = fitz.open(pdf_path)
    images = []
    max_size = 4 * 1024 * 1024  # 4MB порог для JPEG конвертации
    
    for page_num in range(len(doc)):
        page = doc[page_num]
        pix = page.get_pixmap(matrix=fitz.Matrix(4, 4))
        img_data = pix.tobytes("png")
        
        fmt = "PNG"
        if len(img_data) > max_size:
            try:
                from PIL import Image
                img = Image.open(BytesIO(img_data))
                buf = BytesIO()
                img.save(buf, format='JPEG', quality=92)
                img_data = buf.getvalue()
                fmt = "JPEG"
            except ImportError:
                # PIL не установлен — используем PNG как есть
                pass
        
        images.append((img_data, fmt))
        print(f"     Стр.{page_num+1}: {pix.width}x{pix.height}px, {len(img_data)//1024}KB ({fmt})")
    
    doc.close()
    return images


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


def extract_table_anthropic(image_data, api_key, model, media_type="image/png"):
    """Извлечение через Anthropic API"""
    import anthropic
    
    client = anthropic.Anthropic(api_key=api_key)

    image_base64 = base64.b64encode(image_data).decode('utf-8')
    
    message = client.messages.create(
        model=model,
        max_tokens=MAX_TOKENS,
        temperature=0,
        system=SYSTEM_PROMPT,
        messages=[{
            "role": "user",
            "content": [
                {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": image_base64}},
                {"type": "text", "text": EXTRACTION_PROMPT}
            ],
        }],
    )
    
    return parse_json_response(message.content[0].text)


def extract_table_openrouter(image_data, api_key, model, media_type="image/png"):
    """Извлечение через OpenRouter API"""
    import requests

    image_base64 = base64.b64encode(image_data).decode('utf-8')
    
    response = requests.post(
        url="https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        },
        json={
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": f"data:{media_type};base64,{image_base64}"}},
                        {"type": "text", "text": EXTRACTION_PROMPT}
                    ]
                }
            ],
            "max_tokens": MAX_TOKENS,
            "temperature": 0
        },
        timeout=180
    )
    
    if response.status_code != 200:
        raise Exception(f"OpenRouter error: {response.text}")
    
    data = response.json()
    raw_content = data['choices'][0]['message']['content']
    return parse_json_response(raw_content)


def extract_table_openai(image_data, api_key, model, media_type="image/png"):
    """Извлечение через OpenAI API"""
    import openai
    
    client = openai.OpenAI(api_key=api_key)

    image_base64 = base64.b64encode(image_data).decode('utf-8')
    
    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": SYSTEM_PROMPT
            },
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:{media_type};base64,{image_base64}", "detail": "high"}},
                    {"type": "text", "text": EXTRACTION_PROMPT}
                ]
            }
        ],
        max_tokens=MAX_TOKENS,
        temperature=0
    )
    
    return parse_json_response(response.choices[0].message.content)


def parse_json_response(response_text):
    """Парсит JSON из ответа с устойчивостью к ошибкам"""
    # Удаляем markdown обёртку
    json_match = re.search(r'```(?:json)?\s*(.*?)\s*```', response_text, re.DOTALL)
    if json_match:
        json_str = json_match.group(1)
    else:
        json_str = response_text.strip()
    
    # Убираем BOM и невидимые символы
    json_str = json_str.strip('\ufeff\u200b\u200c\u200d')
    
    # Пробуем найти JSON объект если есть лишний текст вокруг
    if not json_str.startswith('{'):
        brace_match = re.search(r'\{.*\}', json_str, re.DOTALL)
        if brace_match:
            json_str = brace_match.group(0)
    
    try:
        data = json.loads(json_str)
        rows = data.get('rows', [])
        
        # Нормализация: убедимся что все строки имеют одинаковую длину (9 колонок)
        if rows:
            max_cols = max(len(row) for row in rows)
            target_cols = max(max_cols, 9)
            for i, row in enumerate(rows):
                if len(row) < target_cols:
                    rows[i] = row + [''] * (target_cols - len(row))
                elif len(row) > target_cols:
                    rows[i] = row[:target_cols]
        
        return {
            'sheet_name': data.get('sheet_name', 'Спецификация'),
            'rows': rows
        }
    except json.JSONDecodeError as e:
        print(f"     ⚠️ JSON parse error: {e}")
        print(f"     Ответ (первые 500 символов): {json_str[:500]}")
        return {'sheet_name': 'Спецификация', 'rows': []}


def extract_table_from_image(image_data, provider, api_key, model, media_type="image/png"):
    """Универсальная функция"""
    if provider == 'anthropic':
        return extract_table_anthropic(image_data, api_key, model, media_type)
    elif provider == 'openrouter':
        return extract_table_openrouter(image_data, api_key, model, media_type)
    elif provider == 'openai':
        return extract_table_openai(image_data, api_key, model, media_type)
    else:
        raise ValueError(f"Неизвестный провайдер: {provider}")


def create_excel_from_pages(pages_data, output_path):
    """Создаёт Excel из данных по страницам.
    
    Каждая страница PDF = отдельный лист Excel.
    Если несколько страниц с одинаковым sheet_name — добавляем номер страницы.
    """
    
    builder = SpecificationExcelBuilder(output_path)
    
    if not pages_data:
        return False
    
    # Собираем sheet_name для каждой страницы, подсчитываем дубликаты
    raw_names = []
    for page_data in pages_data:
        name = page_data.get('sheet_name', 'Спецификация')
        # Убираем "стр" суффикс если модель его добавила
        name = re.sub(r'\s*стр\.?\s*\d*$', '', name).strip()
        raw_names.append(name)
    
    # Подсчёт: сколько раз встречается каждое имя
    from collections import Counter
    name_counts = Counter(raw_names)
    name_seen = Counter()
    
    sheets_created = 0
    for idx, page_data in enumerate(pages_data):
        rows = page_data.get('rows', [])
        if not rows:
            continue
        
        base_name = raw_names[idx]
        page_num = page_data.get('page_num', idx + 1)
        
        # Если имя встречается несколько раз — добавляем "стр.N"
        if name_counts[base_name] > 1:
            name_seen[base_name] += 1
            sheet_name = f"{base_name} стр.{page_num}"
        else:
            sheet_name = base_name
        
        # Excel ограничивает длину имени листа 31 символом
        if len(sheet_name) > 31:
            sheet_name = sheet_name[:28] + f"..{page_num}"
        
        # Убедимся что есть заголовок (первая строка — текстовая)
        if rows and not all(isinstance(cell, str) for cell in rows[0]):
            header = ["Позиция", "Наименование и техническая характеристика",
                     "Тип, марка, обозначение документа, опросного листа",
                     "Код оборудования, изделия, материала",
                     "Завод-изготовитель", "Единица измерения", "Количество",
                     "Масса единицы, кг", "Примечание"]
            rows.insert(0, header)
        
        # Фильтруем мусорные строки
        filtered_rows = []
        for row in rows:
            cell_values = [str(c).strip() for c in row]
            
            # Пропускаем строку если все ячейки — это одиночные цифры 1-9 (нумерация колонок)
            if all(v in ('1','2','3','4','5','6','7','8','9','') for v in cell_values) and \
               any(v in ('1','2','3','4','5','6','7','8','9') for v in cell_values):
                continue
            
            # Пропускаем полностью пустые строки
            if all(v == '' for v in cell_values):
                continue
            
            filtered_rows.append(row)
        
        print(f"     📋 Лист '{sheet_name}': {len(filtered_rows)} строк")
        builder.create_sheet(sheet_name, filtered_rows)
        sheets_created += 1
    
    if sheets_created > 0:
        builder.save()
        return True
    
    return False


def process_pdf(pdf_path: str) -> list:
    """
    Text-first pipeline с fallback на vision.
    
    Для страниц с текстовым слоем — извлекает данные через pdfplumber.
    Для сканов или страниц без текста — fallback на vision OCR.
    """
    import time
    
    pages_data = []
    
    # Проверяем наличие текстового слоя на каждой странице
    print("  🔍 Проверка текстового слоя...")
    text_flags = has_text_layer(pdf_path)
    text_pages = sum(text_flags)
    print(f"     Страниц с текстом: {text_pages}/{len(text_flags)}")
    
    # Ленивая загрузка изображений — только если нужен fallback
    images = None
    
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages):
            page_num = i + 1
            
            if text_flags[i]:
                # --- TEXT-FIRST MODE ---
                print(f"  📝 Страница {page_num}: текстовый режим")
                try:
                    raw_rows, pdf_header = extract_table_from_text(page)
                    if raw_rows and len(raw_rows) > 1:
                        page_data = normalize_table_to_9cols(raw_rows, page_num, pdf_header)
                        page_data['page_num'] = page_num
                        pages_data.append(page_data)
                        print(f"     ✓ '{page_data['sheet_name']}', {len(page_data['rows'])} строк")
                        continue
                    else:
                        print(f"     ⚠️ Пустая таблица, переход на vision-режим")
                except Exception as e:
                    print(f"     ⚠️ Ошибка текстового режима: {e}, переход на vision-режим")
            
            # --- FALLBACK: VISION MODE ---
            print(f"  🖼️ Страница {page_num}: vision-режим (fallback)")
            
            # Загружаем изображения только при первом fallback
            if images is None:
                print("     Генерация изображений...")
                images = pdf_to_images(pdf_path)
            
            # Извлекаем через vision с retry
            image_data, img_fmt = images[i]
            media_type = "image/jpeg" if img_fmt == "JPEG" else "image/png"
            
            success = False
            max_retries = 3
            first_error = None
            
            for attempt in range(max_retries):
                wait_sec = 3
                try:
                    page_data = extract_table_from_image(
                        image_data, API_PROVIDER, API_KEY, MODEL_NAME, media_type
                    )
                    if page_data and page_data.get('rows') and len(page_data['rows']) > 1:
                        page_data['page_num'] = page_num
                        pages_data.append(page_data)
                        print(f"     ✓ Лист '{page_data.get('sheet_name', '?')}', {len(page_data['rows'])} строк")
                        success = True
                        break
                    else:
                        print(f"     ⚠️ Пустой результат (попытка {attempt+1}/{max_retries})")
                except Exception as e:
                    err_str = str(e).lower()
                    is_network = any(k in err_str for k in ('resolve', 'connection', 'timeout', 'nameresolution', 'gaierror'))
                    
                    if first_error is None:
                        first_error = str(e)
                    
                    if is_network:
                        wait_sec = 5 * (attempt + 1)
                        print(f"     🌐 Сетевая ошибка (попытка {attempt+1}/{max_retries}), жду {wait_sec}с: {str(e)[:120]}")
                    else:
                        print(f"     ❌ Ошибка (попытка {attempt+1}/{max_retries}): {str(e)[:200]}")
                
                if attempt < max_retries - 1:
                    time.sleep(wait_sec)
            
            if not success:
                print(f"     ⛔ Страница {page_num} пропущена после {max_retries} попыток")
                if first_error:
                    print(f"     Последняя ошибка: {first_error[:200]}")
    
    return pages_data


@app.route('/convert', methods=['POST'])
def convert_pdf():
    """Конвертация PDF в Excel (text-first с vision fallback)"""
    
    if 'file' not in request.files:
        return jsonify({'error': 'Файл не найден'}), 400
    
    file = request.files['file']
    
    if not file.filename or not allowed_file(file.filename):
        return jsonify({'error': 'Только PDF'}), 400
    
    pdf_path = None
    try:
        filename = secure_filename(file.filename)
        pdf_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(pdf_path)
        
        print(f"\n📄 {filename}")
        if API_PROVIDER and API_KEY:
            print(f"   Vision fallback: {API_PROVIDER}/{MODEL_NAME}")
        else:
            print(f"   ⚠️ API не настроен (только text-режим)")
        
        # Новый text-first pipeline
        pages_data = process_pdf(pdf_path)
        
        if not pages_data:
            return jsonify({'error': 'Нет данных для Excel'}), 500
        
        print("  📊 Создание Excel...")
        output_filename = filename.replace('.pdf', '.xlsx')
        output_path = os.path.join(OUTPUT_FOLDER, output_filename)
        
        if create_excel_from_pages(pages_data, output_path):
            print(f"  ✅ {output_filename}\n")
            return send_file(
                output_path,
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                as_attachment=True,
                download_name=output_filename
            )
        else:
            return jsonify({'error': 'Ошибка создания Excel'}), 500
            
    except Exception as e:
        print(f"❌ {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500
    finally:
        try:
            if pdf_path and os.path.exists(pdf_path):
                os.remove(pdf_path)
        except:
            pass


@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'ok',
        'provider': API_PROVIDER,
        'model': MODEL_NAME,
        'configured': API_KEY is not None
    })


if __name__ == '__main__':
    print("\n" + "="*70)
    print("🚀 Конвертер спецификаций (ИСПРАВЛЕННАЯ ВЕРСИЯ)")
    print("="*70)
    
    if API_PROVIDER and API_KEY:
        print(f"✅ Провайдер: {API_PROVIDER}")
        print(f"✅ Модель: {MODEL_NAME}")
    else:
        print("❌ API не настроен!")
    
    print("\n📝 Откройте: frontend/index.html")
    print("="*70 + "\n")
    
    app.run(debug=True, host='0.0.0.0', port=5000)
