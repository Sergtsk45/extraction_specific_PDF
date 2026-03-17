# План: Внедрение микросервиса invoice-extractor

**Создан:** 2026-03-01  
**Orchestration ID:** orch-2026-03-01-16-57-invoice  
**Статус:** 🟢 Готов к выполнению  
**Всего задач:** 10  
**Приоритет:** High  

---

## Цель проекта

Интегрировать готовый код парсера PDF-счетов (`files_invoice-extractor/`) в мультисервисную платформу DocPlatform в виде нового микросервиса `invoice-extractor` по аналогии с существующим `spec-converterv2`.

---

## Обзор задач

1. **INV-001:** Создание структуры директорий → `services/invoice-extractor/`
2. **INV-002:** Перенос и рефакторинг кода под модульную структуру (вариант А)
3. **INV-003:** Адаптация Flask-приложения (порт 5002, base path, defaults)
4. **INV-004:** Создание `manifest.json` для регистрации в Shell
5. **INV-005:** Создание базового `component.js`
6. **INV-006:** Регистрация в `shell/services.json`
7. **INV-007:** Расширение `dev_server.py` для прокси
8. **INV-008:** Создание `Dockerfile`
9. **INV-009:** Обновление документации проекта
10. **INV-010:** Тестирование интеграции (e2e)

---

## Граф зависимостей

```
INV-001 (структура)
  ├─→ INV-002 (перенос кода)
  │    ├─→ INV-003 (адаптация Flask)
  │    │    └─→ INV-007 (dev_server.py)
  │    └─→ INV-008 (Dockerfile)
  │
  └─→ INV-004 (manifest)
       ├─→ INV-005 (component.js)
       └─→ INV-006 (services.json)

INV-003, INV-004, INV-005 → INV-009 (документация)
INV-003, INV-005, INV-006, INV-007 → INV-010 (тестирование)
```

**Критический путь:** INV-001 → INV-002 → INV-003 → INV-007 → INV-010

---

## Детализация задач

### INV-001: Создание структуры директорий

**Приоритет:** High  
**Время:** ~5 минут  
**Зависимости:** Нет  

**Описание:**

Создать целевую структуру директорий для нового микросервиса по аналогии с `spec-converterv2`:

```
services/invoice-extractor/
├── manifest.json              # Регистрация в Shell
├── component.js               # Web Component
├── backend/
│   ├── app.py                 # Flask: /convert, /health
│   ├── .env.example           # Шаблон переменных окружения
│   ├── requirements.txt       # Python-зависимости
│   ├── gunicorn.conf.py       # Конфигурация Gunicorn
│   └── app/                   # Модули приложения
│       ├── __init__.py
│       ├── extractor.py       # text-first + vision fallback
│       ├── llm_client.py      # Anthropic / OpenAI / OpenRouter
│       ├── normalizer.py      # нормализация данных
│       ├── validators.py      # арифметическая валидация
│       └── excel_builder.py   # формирование xlsx
├── Dockerfile                 # Контейнеризация
├── frontend/
│   └── index.html             # Standalone-режим (опционально)
└── README.md                  # Документация сервиса
```

**Критерии приёмки:**

- [x] Директория `services/invoice-extractor/` создана
- [x] Поддиректории `backend/`, `backend/app/`, `frontend/` созданы
- [x] Все вложенные директории существуют

**Файлы для создания:**

- `services/invoice-extractor/backend/app/__init__.py` (пустой)

---

### INV-002: Перенос и рефакторинг кода под модульную структуру

**Приоритет:** High  
**Время:** ~40 минут  
**Зависимости:** INV-001  

**Описание:**

Перенести код из `files_invoice-extractor/` → `services/invoice-extractor/backend/` с рефакторингом под модульную структуру (вариант А).

**План переноса:**

| Источник | Назначение | Действие |
|----------|-----------|----------|
| `extractor.py` | `backend/app/extractor.py` | Перенести, убедиться что импорты относительные |
| `llm_client.py` | `backend/app/llm_client.py` | Перенести, убедиться что импорты относительные |
| `normalizer.py` | `backend/app/normalizer.py` | Перенести, убедиться что импорты относительные |
| `validators.py` | `backend/app/validators.py` | Перенести, убедиться что импорты относительные |
| `excel_builder.py` | `backend/app/excel_builder.py` | Перенести, убедиться что импорты относительные |
| `requirements.txt` | `backend/requirements.txt` | Перенести как есть |
| `gunicorn.conf.py` | `backend/gunicorn.conf.py` | Перенести как есть |
| `.env.example` | `backend/.env.example` | Перенести как есть |
| `Dockerfile` | `Dockerfile` (корень сервиса) | Перенести, адаптировать пути (см. ниже) |
| `README.md` | `README.md` (корень сервиса) | Перенести, адаптировать под структуру платформы |

**Рефакторинг импортов в модулях:**

Все модули в `backend/app/` должны использовать **относительные импорты**:

```python
# Было в run.py:
from app.extractor import extract_invoice
from app.excel_builder import build_excel
from app.validators import validate_invoice_data

# Станет в backend/app.py:
from app.extractor import extract_invoice
from app.excel_builder import build_excel
from app.validators import validate_invoice_data

# В модулях app/*.py между собой:
# extractor.py:
from app.llm_client import call_vision_llm
from app.normalizer import normalize_invoice

# или
from .llm_client import call_vision_llm
from .normalizer import normalize_invoice
```

**Адаптация Dockerfile:**

Обновить пути в `WORKDIR` и `COPY`:

```dockerfile
# Было:
WORKDIR /app
COPY requirements.txt .
COPY *.py .
COPY app/ app/

# Станет:
WORKDIR /app
COPY backend/requirements.txt .
COPY backend/*.py .
COPY backend/app/ app/
```

**Критерии приёмки:**

- [x] Все 5 модулей перенесены в `backend/app/`
- [x] `backend/app/__init__.py` создан (пустой или с экспортами)
- [x] `requirements.txt`, `gunicorn.conf.py`, `.env.example` в `backend/`
- [x] `Dockerfile` в корне `services/invoice-extractor/`, пути адаптированы
- [x] `README.md` в корне `services/invoice-extractor/`, адаптирован
- [x] Импорты в модулях корректны (относительные)
- [x] Нет битых импортов (проверить с помощью `python -m py_compile`)

**Файлы:**

- `backend/app/extractor.py`
- `backend/app/llm_client.py`
- `backend/app/normalizer.py`
- `backend/app/validators.py`
- `backend/app/excel_builder.py`
- `backend/requirements.txt`
- `backend/gunicorn.conf.py`
- `backend/.env.example`
- `Dockerfile`
- `README.md`

---

### INV-003: Адаптация Flask-приложения (порт, base path, defaults)

**Приоритет:** High  
**Время:** ~30 минут  
**Зависимости:** INV-002  

**Описание:**

Адаптировать `run.py` → `backend/app.py` под требования платформы:

1. **Порт:** изменить с `5000` на `5002`
2. **Base path:** все endpoint'ы теперь под `/api/invoice-extractor/*` (прокси обрабатывается dev_server/nginx)
3. **Default output:** изменить с `both` на `xlsx`
4. **Убрать endpoint:** удалить `GET /download/<job_id>`
5. **URL-encoding заголовков:** кириллические заголовки должны быть URL-encoded (урок из spec-converter)

**Изменения в коде:**

**1. Порт:**

```python
# Было:
port = int(os.getenv("FLASK_PORT", 5000))

# Станет:
port = int(os.getenv("FLASK_PORT", 5002))
```

**2. Default output:**

```python
# Было:
output_mode = request.form.get("output", "both")  # json | xlsx | both

# Станет:
output_mode = request.form.get("output", "xlsx")  # json | xlsx | both
```

**3. Удалить endpoint `/download/<job_id>`:**

Удалить функцию `download()` полностью (строки 119-132 в оригинальном `run.py`).

**4. URL-encoding заголовков:**

Если в заголовках передаётся кириллица (например, имя файла), использовать `urllib.parse.quote()`:

```python
from urllib.parse import quote

# При отправке заголовков:
headers = {
    "X-Vision-Fallback": str(used_vision).lower(),
    "X-Document-Type": "invoice",
    "X-Parse-Quality": parse_quality,
    "X-Job-Id": job_id,
}

# Если нужно передать имя файла или другие кириллические данные в заголовках:
# filename_encoded = quote(filename, safe='')
# headers["X-Filename"] = filename_encoded
```

**5. Логирование:**

Добавить базовое логирование для отладки:

```python
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# В начале /convert:
logger.info(f"[/convert] Получен файл: {file.filename}")

# После обработки:
logger.info(f"[/convert] Обработка завершена: vision={used_vision}, output={output_mode}")
```

**6. Заголовок с документацией по файлу:**

Добавить docstring в начало файла:

```python
"""
@file: app.py
@description: Flask-бэкенд конвертера счетов PDF → Excel.
  Text-first pipeline с fallback на vision OCR (Anthropic / OpenRouter / OpenAI).
  Поддерживает параметры vision_only и provider из запроса (Advanced mode).
  Порт: 5002, Base path: /api/invoice-extractor
@dependencies: app.extractor, app.excel_builder, app.validators, .env
@created: 2026-03-01
"""
```

**Критерии приёмки:**

- [x] Файл `backend/app.py` создан на основе `run.py`
- [x] Порт изменён на `5002`
- [x] Default output = `xlsx`
- [x] Endpoint `/download/<job_id>` удалён
- [x] URL-encoding для кириллических заголовков (если есть)
- [x] Логирование настроено
- [x] Docstring добавлен в начало файла
- [x] Импорты из `app.*` работают корректно
- [x] Flask app запускается без ошибок (`python backend/app.py`)

**Файлы:**

- `backend/app.py` (новый)

---

### INV-004: Создание manifest.json для регистрации в Shell

**Приоритет:** High  
**Время:** ~10 минут  
**Зависимости:** INV-001  

**Описание:**

Создать `manifest.json` по аналогии с `spec-converterv2/manifest.json` для регистрации сервиса в оболочке Shell.

**Содержимое `manifest.json`:**

```json
{
  "id": "invoice-extractor",
  "name": "Парсер счетов",
  "description": "PDF → Excel для счетов (УПД, ТОРГ-12 и др.)",
  "version": "1.0.0",
  "category": "converters",
  "icon": "🧾",
  "component": "component.js",
  "status": "active",
  "accepts": ["application/pdf"],
  "supportsVisionOptions": true,
  "endpoints": {
    "base": "/api/invoice-extractor",
    "convert": "POST /convert",
    "health": "GET /health"
  },
  "maxFileSize": "50MB",
  "outputType": "file-download",
  "outputMime": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
}
```

**Поля:**

- `id`: уникальный идентификатор сервиса (используется в путях)
- `name`: отображаемое имя на карточке
- `description`: краткое описание функциональности
- `version`: версия сервиса (semver)
- `category`: категория для фильтрации в сайдбаре (`converters` / `generators` / `validators`)
- `icon`: эмодзи или путь к иконке
- `component`: имя файла Web Component
- `status`: `active` / `beta` / `deprecated`
- `accepts`: массив MIME-типов принимаемых файлов
- `supportsVisionOptions`: поддержка Vision-режима и выбора провайдера
- `endpoints`: базовый путь и список endpoint'ов
- `maxFileSize`: максимальный размер файла
- `outputType`: тип результата (`file-download` / `json` / `preview`)
- `outputMime`: MIME-тип результата

**Критерии приёмки:**

- [x] Файл `services/invoice-extractor/manifest.json` создан
- [x] Все обязательные поля заполнены
- [x] `id` = `invoice-extractor` (kebab-case)
- [x] `category` = `converters`
- [x] `endpoints.base` = `/api/invoice-extractor`
- [x] `supportsVisionOptions` = `true`
- [x] JSON валиден (проверить с помощью `jq` или `python -m json.tool`)

**Файлы:**

- `services/invoice-extractor/manifest.json`

---

### INV-005: Создание базового component.js

**Приоритет:** Medium  
**Время:** ~20 минут  
**Зависимости:** INV-004  

**Описание:**

Создать базовый `component.js` для отображения сервиса в виде карточки в оболочке Shell. На начальном этапе можно использовать минимальную реализацию без кастомизации (базовый `ServiceCard` из `shell/js/service-registry.js` автоматически рендерит карточки).

**Вариант А (минимальный):** Создать пустой `component.js` с комментарием:

```javascript
/**
 * @file: component.js
 * @description: Web Component для интеграции invoice-extractor в Shell.
 *   На текущем этапе используется базовый ServiceCard из service-registry.js.
 *   Кастомизация UI не требуется.
 * @created: 2026-03-01
 */

// Базовый ServiceCard автоматически рендерится на основе manifest.json
// Дополнительная кастомизация UI будет добавлена в будущих версиях
export default null;
```

**Вариант Б (расширенный):** Создать кастомный Web Component по аналогии с `spec-converterv2/component.js`:

```javascript
/**
 * @file: component.js
 * @description: Web Component для invoice-extractor.
 * @created: 2026-03-01
 */

class InvoiceExtractorCard extends HTMLElement {
  connectedCallback() {
    this.render();
  }

  render() {
    this.innerHTML = `
      <div class="service-card" data-service="invoice-extractor">
        <div class="service-card__icon">🧾</div>
        <h3 class="service-card__title">Парсер счетов</h3>
        <p class="service-card__description">
          PDF → Excel для счетов (УПД, ТОРГ-12 и др.)
        </p>
        <div class="service-card__dropzone">
          Перетащите PDF-файл сюда
        </div>
      </div>
    `;
  }
}

customElements.define('invoice-extractor-card', InvoiceExtractorCard);
```

**Рекомендация:** Использовать **Вариант А** на начальном этапе, чтобы ускорить интеграцию. Кастомизация UI может быть добавлена позже.

**Критерии приёмки:**

- [x] Файл `services/invoice-extractor/component.js` создан
- [x] Docstring добавлен
- [x] Файл валиден (проверить синтаксис ES6)
- [x] Если используется Вариант Б, Web Component определён и экспортирован

**Файлы:**

- `services/invoice-extractor/component.js`

---

### INV-006: Регистрация в shell/services.json

**Приоритет:** High  
**Время:** ~2 минуты  
**Зависимости:** INV-004  

**Описание:**

Добавить `invoice-extractor` в список сервисов в `shell/services.json` для автоматической загрузки оболочкой Shell.

**Текущее содержимое `shell/services.json`:**

```json
{
  "services": [
    "spec-converterv2",
    "ocr",
    "docx-merger",
    "project-validator"
  ]
}
```

**После изменения:**

```json
{
  "services": [
    "spec-converterv2",
    "invoice-extractor",
    "ocr",
    "docx-merger",
    "project-validator"
  ]
}
```

**Критерии приёмки:**

- [x] `invoice-extractor` добавлен в массив `services`
- [x] JSON валиден
- [x] Порядок: `spec-converterv2`, `invoice-extractor`, остальные (для логической группировки реализованных сервисов)

**Файлы:**

- `shell/services.json`

---

### INV-007: Расширение dev_server.py для прокси

**Приоритет:** High  
**Время:** ~15 минут  
**Зависимости:** INV-003  

**Описание:**

Расширить `dev_server.py` для проксирования запросов к новому микросервису:

- Прокси `/api/invoice-extractor/*` → `http://127.0.0.1:5002/*`

**Текущая реализация `dev_server.py`:**

```python
API_PREFIX = "/api/spec-converter"
BACKEND_URL = "http://127.0.0.1:5001"
```

**Изменения:**

1. Поддержка **множественных префиксов** (spec-converter + invoice-extractor)
2. Рефакторинг `_proxy_request()` для динамического выбора бэкенда

**Реализация:**

```python
# Маппинг префиксов → бэкенды
API_ROUTES = {
    "/api/spec-converter": "http://127.0.0.1:5001",
    "/api/invoice-extractor": "http://127.0.0.1:5002",
}

class DevHandler(http.server.SimpleHTTPRequestHandler):
    # ...

    def do_GET(self):
        backend_url = self._match_api_route()
        if backend_url:
            self._proxy_request("GET", backend_url)
        else:
            self._serve_static()

    def do_POST(self):
        backend_url = self._match_api_route()
        if backend_url:
            self._proxy_request("POST", backend_url)
        else:
            self.send_error(405, "Method Not Allowed")

    def _match_api_route(self) -> str | None:
        """Возвращает URL бэкенда, если путь соответствует API-префиксу."""
        for prefix, backend_url in API_ROUTES.items():
            if self.path.startswith(prefix):
                return backend_url
        return None

    def _proxy_request(self, method: str, backend_url: str):
        # Найти префикс
        prefix = None
        for p, url in API_ROUTES.items():
            if backend_url == url:
                prefix = p
                break
        
        backend_path = self.path[len(prefix):] or "/"
        url = f"{backend_url}{backend_path}"
        # ... остальной код прокси без изменений
```

**Критерии приёмки:**

- [x] `API_ROUTES` определён как словарь префиксов
- [x] `/api/invoice-extractor/*` проксируется на `http://127.0.0.1:5002`
- [x] Прокси для `/api/spec-converter/*` работает как раньше
- [x] Метод `_match_api_route()` корректно определяет бэкенд
- [x] GET и POST запросы обрабатываются
- [x] Обновлён вывод в консоль при запуске (показать список прокси)

**Обновить вывод при запуске:**

```python
def main():
    with socketserver.TCPServer(("", PORT), DevHandler) as httpd:
        print(f"\n{'='*60}")
        print(f"  DocPlatform Dev Server — http://localhost:{PORT}")
        print(f"  Прокси:")
        for prefix, backend in API_ROUTES.items():
            print(f"    {prefix} → {backend}")
        print(f"  Убедитесь, что все Flask-бэкенды запущены:")
        print(f"    cd services/spec-converterv2/backend && python app.py")
        print(f"    cd services/invoice-extractor/backend && python app.py")
        print(f"{'='*60}\n")
        httpd.serve_forever()
```

**Файлы:**

- `dev_server.py`

---

### INV-008: Создание Dockerfile

**Приоритет:** Medium  
**Время:** ~10 минут  
**Зависимости:** INV-002  

**Описание:**

Адаптировать `Dockerfile` из `files_invoice-extractor/` для новой структуры директорий.

**Оригинальный Dockerfile:**

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY *.py .
COPY app/ app/
ENV FLASK_HOST=0.0.0.0
ENV FLASK_PORT=5000
EXPOSE 5000
CMD ["gunicorn", "-c", "gunicorn.conf.py", "run:app"]
```

**Адаптированный Dockerfile:**

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Копируем зависимости и устанавливаем
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем код приложения
COPY backend/app.py .
COPY backend/gunicorn.conf.py .
COPY backend/app/ app/

# Переменные окружения
ENV FLASK_HOST=0.0.0.0
ENV FLASK_PORT=5002
ENV PYTHONUNBUFFERED=1

# Открываем порт
EXPOSE 5002

# Запуск через Gunicorn
CMD ["gunicorn", "-c", "gunicorn.conf.py", "app:app"]
```

**Изменения:**

1. Пути адаптированы: `backend/requirements.txt`, `backend/app.py`, `backend/app/`
2. Порт изменён: `5002` вместо `5000`
3. Команда запуска: `app:app` вместо `run:app` (т.к. файл переименован)
4. Добавлен `PYTHONUNBUFFERED=1` для логов в реальном времени

**Критерии приёмки:**

- [x] Файл `services/invoice-extractor/Dockerfile` создан
- [x] Пути адаптированы под новую структуру
- [x] Порт = 5002
- [x] CMD запускает `app:app`
- [x] Dockerfile билдится без ошибок:
  ```bash
  cd services/invoice-extractor
  docker build -t invoice-extractor:dev .
  ```
- [x] Контейнер запускается и отвечает на `/health`:
  ```bash
  docker run -p 5002:5002 --env-file backend/.env invoice-extractor:dev
  curl http://localhost:5002/health
  # {"status": "ok", "version": "1.0.0"}
  ```

**Файлы:**

- `services/invoice-extractor/Dockerfile`

---

### INV-009: Обновление документации

**Приоритет:** Medium  
**Время:** ~20 минут  
**Зависимости:** INV-003, INV-004, INV-005  

**Описание:**

Обновить проектную документацию с учётом нового микросервиса `invoice-extractor`.

**Файлы для обновления:**

1. **`docs/project.md`:**
   - Добавить `invoice-extractor` в раздел **"Роадмап сервисов"** (таблица, статус: Реализован)
   - Добавить краткое описание в раздел **"Компоненты системы"**
   - Обновить диаграмму Mermaid (если есть) — добавить блок `invoice-extractor :5002`

2. **`docs/tasktracker.md`:**
   - Создать запись о задаче "Внедрение микросервиса invoice-extractor"
   - Статус: В процессе / Завершена (в зависимости от момента обновления)
   - Список шагов из этого плана (INV-001 — INV-010)

3. **`docs/changelog.md`:**
   - Добавить запись о добавлении нового сервиса:
     ```markdown
     ## [2026-03-01] - Добавлен микросервис invoice-extractor
     
     ### Добавлено
     - Новый микросервис `invoice-extractor` для парсинга PDF-счетов → Excel
     - Поддержка text-first pipeline + vision fallback (Anthropic/OpenAI/OpenRouter)
     - Интеграция в Shell: manifest, component, регистрация в services.json
     - Прокси в dev_server.py для `/api/invoice-extractor/*` → localhost:5002
     - Dockerfile для контейнеризации сервиса
     
     ### Изменено
     - `dev_server.py`: расширен для поддержки множественных API-префиксов
     - `shell/services.json`: добавлен `invoice-extractor`
     ```

4. **`services/invoice-extractor/README.md`:**
   - Адаптировать README из `files_invoice-extractor/README.md`:
     - Обновить пути: `/convert` → `/api/invoice-extractor/convert`
     - Указать порт: `5002`
     - Добавить раздел "Интеграция в платформу" (ссылки на manifest.json, component.js)
     - Обновить примеры `curl`:
       ```bash
       # Локально (через dev_server.py):
       curl -X POST http://localhost:8080/api/invoice-extractor/convert \
         -F "file=@счет.pdf" \
         -o invoice.xlsx
       
       # Напрямую к бэкенду:
       curl -X POST http://localhost:5002/convert \
         -F "file=@счет.pdf" \
         -o invoice.xlsx
       ```

**Критерии приёмки:**

- [x] `docs/project.md` обновлён (роадмап, архитектура)
- [x] `docs/tasktracker.md` содержит запись о задаче
- [x] `docs/changelog.md` содержит запись о новом сервисе
- [x] `services/invoice-extractor/README.md` адаптирован под платформу
- [x] Все ссылки и пути корректны
- [x] Markdown-файлы валидны (проверить рендеринг)

**Файлы:**

- `docs/project.md`
- `docs/tasktracker.md`
- `docs/changelog.md`
- `services/invoice-extractor/README.md`

---

### INV-010: Тестирование интеграции (e2e)

**Приоритет:** High  
**Время:** ~30 минут  
**Зависимости:** INV-003, INV-005, INV-006, INV-007  

**Описание:**

Провести end-to-end тестирование интеграции нового микросервиса в платформу.

**Сценарии тестирования:**

#### 1. Запуск бэкенда напрямую

```bash
cd services/invoice-extractor/backend
python app.py
```

**Проверки:**

- [x] Бэкенд запускается на порту 5002
- [x] `GET http://localhost:5002/health` возвращает `{"status": "ok", "version": "1.0.0"}`
- [x] Логи показывают успешную инициализацию

#### 2. Тест `/convert` напрямую (text-режим)

```bash
# Использовать тестовый PDF-счёт (если есть в `files_invoice-extractor/`)
curl -X POST http://localhost:5002/convert \
  -F "file=@test_invoice.pdf" \
  -o result.xlsx

# Проверки:
# - HTTP 200 OK
# - Файл result.xlsx создан и валиден (открывается в LibreOffice/Excel)
# - Заголовок X-Vision-Fallback: false (для текстовых PDF)
```

#### 3. Тест `/convert` напрямую (vision-режим)

```bash
curl -X POST http://localhost:5002/convert \
  -F "file=@test_invoice.pdf" \
  -F "vision_only=true" \
  -F "provider=anthropic" \
  -o result_vision.xlsx

# Проверки:
# - HTTP 200 OK
# - Заголовок X-Vision-Fallback: true
# - Файл result_vision.xlsx создан и валиден
```

#### 4. Запуск через dev_server.py (прокси)

```bash
# Терминал 1: запустить бэкенд
cd services/invoice-extractor/backend
python app.py

# Терминал 2: запустить dev_server
cd project-root
python dev_server.py

# Терминал 3: отправить запрос через прокси
curl -X POST http://localhost:8080/api/invoice-extractor/convert \
  -F "file=@test_invoice.pdf" \
  -o result_proxy.xlsx

# Проверки:
# - HTTP 200 OK
# - Прокси корректно перенаправляет на :5002
# - Файл result_proxy.xlsx создан и валиден
```

#### 5. Проверка Shell UI (браузер)

```bash
# Запустить dev_server.py
python dev_server.py

# Открыть браузер:
# http://localhost:8080
```

**Проверки:**

- [x] Карточка `invoice-extractor` отображается в сетке
- [x] Иконка 🧾, название "Парсер счетов", описание корректны
- [x] Drag-and-drop зона активна
- [x] При перетаскивании PDF-файла:
  - Карточка показывает прогресс
  - После обработки автоматически скачивается `.xlsx`
  - Логи в консоли браузера показывают успешный вызов API
  - Нет ошибок в консоли (404, CORS, и т.п.)

#### 6. Проверка фильтрации в сайдбаре

- [x] В сайдбаре выбрать категорию "Конвертеры"
- [x] Карточки `spec-converterv2` и `invoice-extractor` видны
- [x] Остальные категории скрыты

#### 7. Docker-тест (опционально, если требуется)

```bash
cd services/invoice-extractor
docker build -t invoice-extractor:dev .
docker run -p 5002:5002 --env-file backend/.env invoice-extractor:dev

# В другом терминале:
curl http://localhost:5002/health
# {"status": "ok", "version": "1.0.0"}
```

**Чек-лист приёмки:**

- [x] Все 7 тестовых сценариев пройдены
- [x] Нет ошибок в консоли браузера
- [x] Нет ошибок в логах Flask
- [x] Нет ошибок в логах dev_server.py
- [x] `.xlsx` файлы открываются корректно
- [x] URL-encoded заголовки корректно декодируются (если применимо)
- [x] Прокси работает для обоих сервисов (`spec-converter` и `invoice-extractor`)

**Файлы для проверки:**

- `services/invoice-extractor/backend/app.py`
- `dev_server.py`
- `shell/services.json`
- `services/invoice-extractor/manifest.json`
- `services/invoice-extractor/component.js`

---

## Архитектурные решения

### Выбор структуры (вариант А — модульная)

Код организован в директорию `backend/app/` с отдельными модулями:

- `extractor.py` — основная логика извлечения
- `llm_client.py` — работа с LLM API
- `normalizer.py` — нормализация данных
- `validators.py` — валидация
- `excel_builder.py` — генерация Excel

**Преимущества:**

- Чёткое разделение ответственности
- Удобство тестирования (каждый модуль можно тестировать отдельно)
- Масштабируемость (легко добавлять новые модули)
- Соответствие структуре существующего `spec-converterv2`

### Default output = xlsx

Платформа ориентирована на практическое использование → пользователи ожидают готовый файл Excel. JSON-режим доступен через параметр `output=json` для отладки и интеграций.

### Удаление endpoint `/download/<job_id>`

Shell работает в режиме "один запрос → один ответ". Job ID не используется для последующих скачиваний. Упрощает архитектуру и снижает количество временных файлов на диске.

### URL-encoding кириллических заголовков

HTTP-заголовки должны быть ASCII/latin-1. При передаче кириллицы (например, имён файлов) используется URL-encoding (`urllib.parse.quote()`). Фронтенд декодирует через `decodeURIComponent()`.

**Урок из spec-converter:** Раньше передавалась сырая кириллица в `X-Sheet-Names` → HTTP 502 на некоторых прокси. После внедрения URL-encoding проблема исчезла.

---

## Метрики успеха

| Метрика | Целевое значение |
|---------|-----------------|
| Все 10 задач завершены | 100% |
| Бэкенд запускается без ошибок | ✅ |
| `/health` отвечает корректно | ✅ |
| `/convert` обрабатывает PDF → xlsx | ✅ |
| Карточка отображается в Shell | ✅ |
| Прокси работает через dev_server.py | ✅ |
| Документация обновлена | ✅ |
| E2E тесты пройдены | 7/7 |

---

## Риски и митигация

| Риск | Вероятность | Влияние | Митигация |
|------|-------------|---------|-----------|
| Битые импорты после переноса | Средняя | Высокое | Проверить с `python -m py_compile`, запустить `app.py` |
| Конфликт портов (5002 занят) | Низкая | Среднее | Проверить перед запуском: `lsof -i :5002` |
| CORS-ошибки в браузере | Низкая | Среднее | `flask-cors` уже подключён, dev_server проксирует |
| Несоответствие manifest.json и реального API | Средняя | Высокое | Провести тщательное тестирование INV-010 |
| URL-encoding не работает | Низкая | Среднее | Тестировать с кириллическими именами файлов |

---

## План выполнения (рекомендуемая последовательность)

### Фаза 1: Базовая структура (параллельно)

- **INV-001** (структура) + **INV-004** (manifest) — можно выполнять параллельно

### Фаза 2: Перенос кода (последовательно)

- **INV-002** (перенос кода) → **INV-003** (адаптация Flask)

### Фаза 3: Frontend-интеграция (параллельно)

- **INV-005** (component.js) + **INV-006** (services.json) — независимы

### Фаза 4: Dev-инфраструктура (последовательно)

- **INV-007** (dev_server) — зависит от INV-003
- **INV-008** (Dockerfile) — зависит от INV-002, может идти параллельно с INV-007

### Фаза 5: Финализация (параллельно)

- **INV-009** (документация) — можно начать после INV-003, INV-004, INV-005
- **INV-010** (тестирование) — только после INV-003, INV-005, INV-006, INV-007

**Общее время:** ~3-4 часа (с учётом тестирования и отладки)

---

## Прогресс выполнения

*(Обновляется orchestrator'ом в процессе выполнения)*

- ⏳ **INV-001:** Создание структуры директорий (Pending)
- ⏳ **INV-002:** Перенос и рефакторинг кода (Pending)
- ⏳ **INV-003:** Адаптация Flask-приложения (Pending)
- ⏳ **INV-004:** Создание manifest.json (Pending)
- ⏳ **INV-005:** Создание component.js (Pending)
- ⏳ **INV-006:** Регистрация в services.json (Pending)
- ⏳ **INV-007:** Расширение dev_server.py (Pending)
- ⏳ **INV-008:** Создание Dockerfile (Pending)
- ⏳ **INV-009:** Обновление документации (Pending)
- ⏳ **INV-010:** Тестирование интеграции (Pending)

---

**Итого:** 10 задач, 0 завершено, 0 в процессе.

---

*План создан: 2026-03-01 16:57*  
*Orchestration ID: orch-2026-03-01-16-57-invoice*
