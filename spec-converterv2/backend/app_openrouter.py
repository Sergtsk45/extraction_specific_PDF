from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
import os
from openai import OpenAI
import fitz  # PyMuPDF
import base64
import json
import re
from pathlib import Path
from werkzeug.utils import secure_filename
from spec_utils import SpecificationExcelBuilder, SpecificationDataExtractor

app = Flask(__name__)
CORS(app)

# Конфигурация
UPLOAD_FOLDER = '../uploads'
OUTPUT_FOLDER = '../output'
ALLOWED_EXTENSIONS = {'pdf'}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# Загружаем API ключ из config.py
try:
    from config import OPENROUTER_API_KEY, MODEL_NAME
except ImportError:
    print("⚠️  ВНИМАНИЕ: config.py не найден!")
    print("   Создайте файл config.py:")
    print("   OPENROUTER_API_KEY = 'your-api-key-here'")
    print("   MODEL_NAME = 'anthropic/claude-sonnet-4'")
    OPENROUTER_API_KEY = None
    MODEL_NAME = 'anthropic/claude-sonnet-4'


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def pdf_to_images(pdf_path):
    """Конвертирует PDF в список изображений"""
    doc = fitz.open(pdf_path)
    images = []
    
    for page_num in range(len(doc)):
        page = doc[page_num]
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
        img_data = pix.tobytes("png")
        images.append(img_data)
    
    doc.close()
    return images


def extract_table_from_image_openrouter(image_data, api_key, model):
    """Извлекает таблицу из изображения через OpenRouter API"""
    
    # OpenRouter использует OpenAI-совместимый API
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key
    )
    
    # Промпт для извлечения таблицы
    prompt = """Извлеки данные из этой страницы спецификации в JSON формат.

Структура таблицы (9 колонок):
1. Позиция (может быть пустой для подпунктов)
2. Наименование и техническая характеристика
3. Тип, марка, обозначение документа, опросного листа
4. Код оборудования/изделия/материала (или "Код продукции" для офисов)
5. Завод-изготовитель (или "Поставщик")
6. Единица измерения
7. Количество
8. Масса единицы, кг
9. Примечание

ВАЖНО:
- Если позиция пустая, это значит продолжение предыдущей позиции (оставь пустой строкой "")
- Многострочный текст в одной ячейке объедини через пробел
- "в т.ч.:" означает, что дальше идут компоненты узла
- Сохрани все специальные символы: Ф, ², м³, °С, ±

Верни ТОЛЬКО JSON без дополнительного текста:
{
  "rows": [
    ["позиция", "наименование", "тип", "код", "завод", "ед.изм", "кол-во", "масса", "примечание"],
    ...
  ]
}"""

    # Конвертируем изображение в base64
    image_base64 = base64.b64encode(image_data).decode('utf-8')
    
    # Вызов OpenRouter API
    completion = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{image_base64}"
                        }
                    },
                    {
                        "type": "text",
                        "text": prompt
                    }
                ]
            }
        ],
        max_tokens=4000
    )
    
    # Извлекаем текст ответа
    response_text = completion.choices[0].message.content
    
    # Парсим JSON
    json_match = re.search(r'```json\s*(.*?)\s*```', response_text, re.DOTALL)
    if json_match:
        json_str = json_match.group(1)
    else:
        json_str = response_text
    
    try:
        data = json.loads(json_str)
        return data.get('rows', [])
    except json.JSONDecodeError as e:
        print(f"JSON parse error: {e}")
        print(f"Response: {response_text[:500]}")
        return []


def create_excel_from_data(all_rows, output_path):
    """Создаёт Excel из извлечённых данных"""
    
    builder = SpecificationExcelBuilder(output_path)
    ext = SpecificationDataExtractor()
    
    if all_rows:
        if len(all_rows) > 0 and not all(isinstance(cell, str) for cell in all_rows[0]):
            header = ext.create_header(use_code_column=False)
            all_rows.insert(0, header)
        
        builder.create_sheet("Спецификация", all_rows)
        builder.save()
        return True
    
    return False


@app.route('/convert', methods=['POST'])
def convert_pdf():
    """Основной endpoint для конвертации PDF в Excel"""
    
    if not OPENROUTER_API_KEY:
        return jsonify({'error': 'API ключ не настроен. Добавьте OPENROUTER_API_KEY в config.py'}), 500
    
    if 'file' not in request.files:
        return jsonify({'error': 'Файл не найден'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'error': 'Файл не выбран'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'error': 'Разрешены только PDF файлы'}), 400
    
    try:
        filename = secure_filename(file.filename)
        pdf_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(pdf_path)
        
        print(f"📄 Обработка файла: {filename}")
        print(f"🤖 Используется модель: {MODEL_NAME}")
        
        # Конвертируем PDF в изображения
        print("  🖼️  Конвертация страниц в изображения...")
        images = pdf_to_images(pdf_path)
        print(f"  ✓ Создано {len(images)} изображений")
        
        # Обрабатываем каждую страницу через OpenRouter
        all_rows = []
        
        for i, image in enumerate(images):
            print(f"  🤖 Обработка страницы {i+1}/{len(images)} через OpenRouter...")
            
            try:
                rows = extract_table_from_image_openrouter(image, OPENROUTER_API_KEY, MODEL_NAME)
                if rows:
                    all_rows.extend(rows)
                    print(f"     ✓ Извлечено {len(rows)} строк")
                else:
                    print(f"     ⚠️  Нет данных на странице")
            except Exception as e:
                print(f"     ❌ Ошибка на странице {i+1}: {e}")
                continue
        
        if not all_rows:
            return jsonify({'error': 'Не удалось извлечь данные из PDF'}), 500
        
        # Создаём Excel
        print("  📊 Создание Excel файла...")
        output_filename = filename.replace('.pdf', '.xlsx')
        output_path = os.path.join(OUTPUT_FOLDER, output_filename)
        
        if create_excel_from_data(all_rows, output_path):
            print(f"  ✅ Excel создан: {output_filename}")
            
            return send_file(
                output_path,
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                as_attachment=True,
                download_name=output_filename
            )
        else:
            return jsonify({'error': 'Ошибка создания Excel'}), 500
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500
    
    finally:
        try:
            if os.path.exists(pdf_path):
                os.remove(pdf_path)
        except:
            pass


@app.route('/health', methods=['GET'])
def health_check():
    """Проверка работоспособности сервера"""
    return jsonify({
        'status': 'ok',
        'api_key_configured': OPENROUTER_API_KEY is not None,
        'model': MODEL_NAME
    })


if __name__ == '__main__':
    print("\n" + "="*60)
    print("🚀 Запуск сервера конвертации спецификаций")
    print("   (OpenRouter версия)")
    print("="*60)
    
    if OPENROUTER_API_KEY:
        print("✅ API ключ настроен")
        print(f"🤖 Модель: {MODEL_NAME}")
    else:
        print("❌ API ключ НЕ настроен!")
        print("   Создайте файл backend/config.py:")
        print("   OPENROUTER_API_KEY = 'sk-or-...'")
        print("   MODEL_NAME = 'anthropic/claude-sonnet-4'")
    
    print("\n📝 Откройте в браузере:")
    print("   file:///path/to/frontend/index.html")
    print("\n" + "="*60 + "\n")
    
    app.run(debug=True, host='0.0.0.0', port=5000)
