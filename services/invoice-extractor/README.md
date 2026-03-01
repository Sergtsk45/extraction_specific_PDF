/**
 * @file: README.md
 * @description: Документация микросервиса invoice-extractor
 * @dependencies: Flask, pdfplumber, PyMuPDF, openpyxl, Anthropic/OpenAI/OpenRouter
 * @created: 2026-03-01
 */

# Invoice Extractor — Парсер счетов поставщиков

## 🎯 Описание

Микросервис для автоматического извлечения структурированных данных из PDF-счетов поставщиков (счёт-фактура, счёт, накладная и т.п.) с последующим экспортом в Excel-файл (.xlsx).

**Основные возможности:**
- ✅ Text-first пайплайн для быстрой обработки (2-5 сек)
- 👁 LLM Vision fallback для отсканированных/сложных документов (~30-60 сек)
- 📊 Экспорт структурированных данных в XLSX с форматированием
- 🔍 Валидация качества парсинга с системой предупреждений
- 🔄 Поддержка нескольких LLM-провайдеров (Anthropic, OpenAI, OpenRouter)
- 🏗️ Встраивание в Shell App через Web Component или автономный режим

---

## 📋 Требования

### Система
- **Python**: ≥ 3.11
- **ОС**: Linux (WSL2), macOS, Windows (с Python)

### Зависимости (Python)
```
flask>=3.0.0              # REST API фреймворк
flask-cors>=4.0.0         # CORS поддержка
python-dotenv>=1.0.0      # Управление переменными окружения
pdfplumber>=0.11.0        # Извлечение текста из PDF
PyMuPDF>=1.24.0          # PDF-рендеринг (Image to LLM)
openpyxl>=3.1.0          # Генерация Excel-файлов
anthropic>=0.30.0         # Anthropic Claude API
openai>=1.40.0            # OpenAI API (включая OpenRouter)
requests>=2.32.0          # HTTP-клиент
gunicorn>=22.0.0          # Production WSGI-сервер
Pillow>=10.0.0            # Обработка изображений
```

---

## 🚀 Быстрый старт

### 1. Установка

```bash
# Перейти в директорию микросервиса
cd services/invoice-extractor/backend

# Создать виртуальное окружение (опционально, но рекомендуется)
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
# или
venv\Scripts\activate     # Windows

# Установить зависимости
pip install -r requirements.txt
```

### 2. Конфигурация (`.env`)

```bash
# Скопировать шаблон
cp .env.example .env

# Отредактировать .env со своими ключами
nano .env  # или ваш редактор
```

**Пример `.env`:**
```
# LLM Configuration
LLM_PROVIDER=anthropic                    # anthropic | openai | openrouter
ANTHROPIC_API_KEY=sk-ant-...              # Ключ Anthropic
OPENAI_API_KEY=sk-...                     # Ключ OpenAI / OpenRouter
OPENROUTER_API_KEY=sk-or-...              # Ключ OpenRouter

# Server Configuration
FLASK_HOST=0.0.0.0
FLASK_PORT=5002
FLASK_DEBUG=false

# File Management
UPLOAD_FOLDER=uploads                     # Папка для загруженных PDF
OUTPUT_FOLDER=outputs                     # Папка для выходных XLSX
MAX_FILE_SIZE_MB=50                       # Максимальный размер файла

# CORS
ALLOWED_ORIGINS=http://localhost:8080,http://localhost:5002
```

### 3. Запуск (разработка)

```bash
# Простой запуск
python3 app.py

# Dev-сервер автоматически доступен на:
# http://localhost:5002/api/invoice-extractor/health
# http://localhost:5002/api/invoice-extractor/convert (POST)
```

### 4. Проверка здоровья

```bash
curl -X GET http://localhost:5002/api/invoice-extractor/health
# Ответ: {"status": "ok", "version": "1.0.0", "service": "invoice-extractor"}
```

---

## 📡 API Endpoints

### `GET /api/invoice-extractor/health`

**Описание:** Проверка статуса микросервиса

**Ответ (200 OK):**
```json
{
  "status": "ok",
  "version": "1.0.0",
  "service": "invoice-extractor"
}
```

---

### `POST /api/invoice-extractor/convert`

**Описание:** Парсинг PDF-счета и экспорт в XLSX

**Request (multipart/form-data):**
- `file` *(binary, обязательно)* — PDF-файл счета
- `provider` *(optional, default: anthropic)* — LLM провайдер:
  - `anthropic` — Anthropic Claude API
  - `openai` — OpenAI GPT-4V / OpenRouter
  - `openrouter` — OpenRouter (если используется как базовый провайдер)
- `vision_only` *(optional, default: false)* — 'true' | 'false' — принудительно использовать LLM Vision
- `output` *(optional, default: xlsx)* — Тип возвращаемых данных:
  - `xlsx` — XLSX-файл (файл скачивается)
  - `json` — JSON с извлечёнными данными
  - `both` — JSON + ссылка на XLSX

**Пример запроса (cURL):**
```bash
# Быстрый парс с дефолтным провайдером (text-first)
curl -X POST \
  -F "file=@invoice.pdf" \
  http://localhost:5002/api/invoice-extractor/convert \
  --output result.xlsx

# С параметрами
curl -X POST \
  -F "file=@invoice.pdf" \
  -F "provider=openai" \
  -F "vision_only=true" \
  -F "output=json" \
  http://localhost:5002/api/invoice-extractor/convert
```

**Успешный ответ (200 OK):**

Заголовки ответа:
```
X-Vision-Fallback: true/false              # Использовался ли Vision
X-Document-Type: invoice
X-Parse-Quality: ok/partial                # Качество парсинга
X-Job-Id: uuid                             # Уникальный идентификатор задачи
X-Invoice-Number: INV-20260301-001         # Номер счета (URL-encoded)
```

**Режим `output=xlsx` (default):**
- Возвращается XLSX-файл с заголовками выше
- Имя файла: `invoice_{invoice_number}.xlsx`

**Режим `output=json`:**
```json
{
  "invoice_number": "INV-20260301-001",
  "invoice_date": "2026-03-01",
  "supplier": {
    "name": "ООО Поставщик",
    "inn": "1234567890",
    "address": "Москва, ул. Примерная, д. 1"
  },
  "buyer": {
    "name": "ООО Покупатель",
    "inn": "0987654321",
    "address": "СПб, пр. Невский, д. 100"
  },
  "items": [
    {
      "description": "Товар 1",
      "quantity": 10,
      "unit": "шт",
      "unit_price": 100.00,
      "total_price": 1000.00
    }
  ],
  "total_amount": 1000.00,
  "vat_amount": 180.00,
  "total_with_vat": 1180.00,
  "warnings": ["Warning message"],
  "parse_quality": "ok"
}
```

**Ошибка (400/500):**
```json
{
  "error": "Описание ошибки",
  "job_id": "uuid"
}
```

---

## 🔧 Конфигурация

### Переменные окружения (`.env`)

| Переменная | Default | Описание |
|-----------|---------|----------|
| `LLM_PROVIDER` | `anthropic` | Основной LLM провайдер (anthropic/openai/openrouter) |
| `ANTHROPIC_API_KEY` | - | Ключ Anthropic Claude API |
| `OPENAI_API_KEY` | - | Ключ OpenAI (включая OpenRouter как совместимый сервис) |
| `OPENROUTER_API_KEY` | - | Ключ OpenRouter (если используется как провайдер) |
| `FLASK_HOST` | `0.0.0.0` | Хост для привязки сервера |
| `FLASK_PORT` | `5002` | Порт микросервиса |
| `FLASK_DEBUG` | `false` | Режим отладки (true/false) |
| `UPLOAD_FOLDER` | `uploads` | Папка для временных PDF |
| `OUTPUT_FOLDER` | `outputs` | Папка для выходных XLSX |
| `MAX_FILE_SIZE_MB` | `50` | Максимальный размер загружаемого файла (МБ) |
| `ALLOWED_ORIGINS` | `http://localhost:8080` | CORS allowed origins (запятая-разделяемый список) |

### Логирование

Сервис логирует в stdout/stderr с форматом:
```
2026-03-01 12:34:56,789 - app - INFO - Convert request received
2026-03-01 12:34:57,123 - app - INFO - Processing file: invoice.pdf, provider: anthropic, output: xlsx
```

---

## 🐳 Docker

### Dockerfile

Микросервис поставляется с готовым `Dockerfile` для контейнеризации.

**Сборка образа:**
```bash
docker build -t invoice-extractor:latest .
```

**Запуск контейнера:**
```bash
docker run \
  -p 5002:5002 \
  -e ANTHROPIC_API_KEY=sk-ant-... \
  -e OPENAI_API_KEY=sk-... \
  -v $(pwd)/uploads:/app/uploads \
  -v $(pwd)/outputs:/app/outputs \
  invoice-extractor:latest
```

### Docker Compose

Для полного стека (Shell + spec-converterv2 + invoice-extractor):
```bash
docker-compose up
```

Сервис будет доступен на `http://localhost/api/invoice-extractor/*` через Nginx Gateway.

---

## 🧪 Тестирование

### Ручное тестирование

1. **Standalone режим** (автономный):
   ```bash
   # Открыть фронтенд напрямую
   python3 -m http.server 8000 --directory .
   # Затем открыть в браузере: http://localhost:8000/frontend/index.html
   ```

2. **Через Shell App** (встраивание):
   - Запустить Shell App dev-сервер (`cd ../../.. && python3 dev_server.py`)
   - Запустить backend микросервиса (`python3 app.py`)
   - Открыть http://localhost:8080, найти карточку "Парсер счетов"

### Проверка API

```bash
# Загрузить тестовый PDF и получить JSON
curl -X POST \
  -F "file=@test_invoice.pdf" \
  -F "output=json" \
  http://localhost:5002/api/invoice-extractor/convert \
  | jq .

# Принудить Vision-режим
curl -X POST \
  -F "file=@test_invoice.pdf" \
  -F "vision_only=true" \
  -F "provider=openai" \
  http://localhost:5002/api/invoice-extractor/convert \
  --output result_vision.xlsx
```

---

## 📁 Структура проекта

```
services/invoice-extractor/
├── component.js                    # Web Component для Shell App
├── manifest.json                   # Манифест микросервиса
├── Dockerfile                      # Docker контейнеризация
├── frontend/
│   └── index.html                  # Standalone UI (автономный режим)
├── backend/
│   ├── app.py                      # Flask приложение (main entry point)
│   ├── app/
│   │   ├── __init__.py
│   │   ├── extractor.py            # Основной парсер (text-first + Vision)
│   │   ├── llm_client.py           # Клиент для LLM (Anthropic, OpenAI, OpenRouter)
│   │   ├── excel_builder.py        # Генератор Excel-файлов (openpyxl)
│   │   ├── validators.py           # Валидация извлечённых данных
│   │   └── normalizer.py           # Нормализация и очистка данных
│   ├── .env                        # Конфиг (не в репо, создать самостоятельно)
│   ├── .env.example                # Шаблон .env для репозитория
│   ├── requirements.txt            # Python зависимости
│   ├── gunicorn.conf.py            # Конфиг Gunicorn для production
│   ├── uploads/                    # Папка для временных PDF (git-ignored)
│   └── outputs/                    # Папка для выходных XLSX (git-ignored)
├── README.md                       # Документация (этот файл)
└── start.sh                        # Script для быстрого старта
```

---

## 🔐 Безопасность

### Текущие меры
- ✅ Валидация расширения файла (только `.pdf`)
- ✅ Ограничение размера файла (по умолчанию 50 МБ)
- ✅ API-ключи в `.env` (не в репозитории через `.gitignore`)
- ✅ CORS ограничение allowed origins
- ✅ Валидация путей (защита от Path Traversal)
- ✅ Автоматическое удаление временных файлов после обработки
- ✅ Безопасная кодировка заголовков (URL-encoding для кириллицы)

### Рекомендации для production
1. **Аутентификация**: Включить Basic Auth через Nginx (опционально)
2. **Rate Limiting**: Настроить ограничение запросов на уровне Gateway
3. **Мониторинг**: Логировать все ошибки парсинга для анализа
4. **Аудит зависимостей**: Периодически запускать `pip audit`

---

## 🐛 Troubleshooting

### Проблема: "ModuleNotFoundError: No module named 'anthropic'"
```bash
# Решение: установить зависимости
pip install -r requirements.txt
```

### Проблема: "HTTP 502 при конвертации"
**Причина:** Обычно падение Flask-бэкенда при обработке больших файлов  
**Решение:** Проверить логи, увеличить `MAX_FILE_SIZE_MB` в `.env`, перезапустить сервис

### Проблема: "Vision-режим не включается"
**Причина:** API-ключ не установлен или неверный  
**Решение:** Проверить `.env`, убедиться, что `ANTHROPIC_API_KEY` или `OPENAI_API_KEY` установлены

### Проблема: Временные PDF не удаляются
**Причина:** Сервис был убит, папка uploads переполнена  
**Решение:** Вручную очистить `backend/uploads/`, перезапустить

---

## 📝 Примеры использования

### Встраивание в Python
```python
from app.extractor import extract_invoice
from app.excel_builder import build_excel

# Парсить PDF
invoice_data, used_vision = extract_invoice(
    pdf_path="invoice.pdf",
    vision_only=False,
    provider="anthropic"
)

# Построить Excel
build_excel(invoice_data, "output.xlsx")

print(f"Используется Vision: {used_vision}")
print(f"Качество: {invoice_data.get('parse_quality', 'unknown')}")
```

### cURL примеры
```bash
# Быстрая конвертация (text-first)
curl -X POST -F "file=@invoice.pdf" \
  http://localhost:5002/api/invoice-extractor/convert \
  --output result.xlsx

# Только Vision (для сложных документов)
curl -X POST \
  -F "file=@scanned_invoice.pdf" \
  -F "vision_only=true" \
  -F "provider=openai" \
  http://localhost:5002/api/invoice-extractor/convert \
  --output result_vision.xlsx

# Получить JSON с данными
curl -X POST \
  -F "file=@invoice.pdf" \
  -F "output=json" \
  http://localhost:5002/api/invoice-extractor/convert \
  | python3 -m json.tool
```

---

## 🔗 Интеграция с Shell App

Микросервис автоматически регистрируется в Shell App через манифест `manifest.json`:

```json
{
  "id": "invoice-extractor",
  "name": "Парсер счетов",
  "category": "converters",
  "endpoints": {
    "base": "/api/invoice-extractor",
    "convert": "POST /convert",
    "health": "GET /health"
  }
}
```

Карточка появится в сетке автоматически после перезагрузки Shell App.

---

## 📞 Поддержка

- **Документация проекта**: `/docs/project.md`
- **Задачи**: `/docs/tasktracker.md` (INV-001 до INV-010)
- **История изменений**: `/docs/changelog.md`

---

*Документация обновляется при изменении API, функциональности или конфигурации.*
