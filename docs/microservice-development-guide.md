# Руководство по разработке микросервисов

> **Версия:** 1.0  
> **Дата:** 2026-03-01  
> **Платформа:** Extraction Specific PDF (DocPlatform)

Данный документ — пошаговая инструкция для разработчиков, создающих новые микросервисы для интеграции в мультисервисную платформу DocPlatform.

---

## Содержание

1. [Обзор архитектуры](#1-обзор-архитектуры)
2. [Структура микросервиса](#2-структура-микросервиса)
3. [Шаг 1 — Создание каталога и скаффолдинг](#3-шаг-1--создание-каталога-и-скаффолдинг)
4. [Шаг 2 — Манифест (manifest.json)](#4-шаг-2--манифест-manifestjson)
5. [Шаг 3 — Backend (Flask API)](#5-шаг-3--backend-flask-api)
6. [Шаг 4 — Web Component (component.js)](#6-шаг-4--web-component-componentjs)
7. [Шаг 5 — Standalone-фронтенд](#7-шаг-5--standalone-фронтенд)
8. [Шаг 6 — Docker](#8-шаг-6--docker)
9. [Шаг 7 — Регистрация в платформе](#9-шаг-7--регистрация-в-платформе)
10. [Шаг 8 — Запуск и отладка](#10-шаг-8--запуск-и-отладка)
11. [API-контракт](#11-api-контракт)
12. [Переменные окружения](#12-переменные-окружения)
13. [Безопасность](#13-безопасность)
14. [Тестирование](#14-тестирование)
15. [Стандарты кода](#15-стандарты-кода)
16. [Чеклист перед релизом](#16-чеклист-перед-релизом)
17. [Примеры из существующих сервисов](#17-примеры-из-существующих-сервисов)
18. [FAQ](#18-faq)

---

## 1. Обзор архитектуры

Платформа построена по микросервисной модели с единой SPA-оболочкой (Shell App):

```
Браузер → Shell App (SPA, порт 8080)
  └── Загружает services.json → манифесты → component.js
  └── Карточки сервисов (Web Components, Shadow DOM)
  └── API-запросы через прокси:
        /api/{service-id}/* → localhost:{port}/*
```

**Ключевые принципы:**

| Принцип | Описание |
|---------|----------|
| **Plug-and-play** | Новый сервис подключается без модификации Shell App |
| **Dual mode** | Каждый сервис работает и встроенно (через Shell), и автономно (свой `index.html`) |
| **Независимость** | Собственный стек, зависимости, деплой, порт |
| **Изоляция отказов** | Падение сервиса не влияет на оболочку и другие сервисы |
| **Stateless** | Нет централизованной БД; состояние в `localStorage` браузера |

---

## 2. Структура микросервиса

Каждый микросервис располагается в `services/{service-id}/` и следует стандартной структуре:

```
services/{service-id}/
├── manifest.json              # Манифест для Shell App (обязательно)
├── component.js               # Web Component для встраивания (обязательно)
├── Dockerfile                 # Контейнеризация (обязательно)
├── README.md                  # Документация сервиса
├── start.sh                   # Скрипт запуска (опционально)
├── frontend/
│   └── index.html             # Standalone-режим (обязательно)
└── backend/
    ├── app.py                 # Flask: точка входа, роуты
    ├── wsgi.py                # WSGI-точка входа для Gunicorn
    ├── gunicorn.conf.py       # Конфигурация Gunicorn
    ├── requirements.txt       # Python-зависимости
    ├── .env                   # Секреты (не в репо, в .gitignore)
    ├── .env.example           # Шаблон переменных окружения (в репо)
    ├── uploads/               # Временные загрузки (в .gitignore)
    ├── outputs/               # Результаты обработки (в .gitignore)
    └── app/                   # Бизнес-логика (опционально, для сложных сервисов)
        ├── __init__.py
        ├── processor.py       # Основной обработчик
        └── ...
```

---

## 3. Шаг 1 — Создание каталога и скаффолдинг

### 3.1 Выбор идентификатора

Идентификатор сервиса (`service-id`) используется повсеместно: имя каталога, тег Custom Element, маршрут API, имя systemd unit.

**Правила именования:**
- Формат: `kebab-case` (строчные латинские буквы, дефисы)
- Примеры: `ocr-extractor`, `docx-merger`, `project-validator`
- Запрещено: пробелы, подчёркивания, заглавные буквы, кириллица

### 3.2 Выбор порта

Порты выделяются последовательно:

| Порт | Сервис |
|------|--------|
| 5001 | spec-converterv2 |
| 5002 | invoice-extractor |
| 5003 | *следующий сервис* |
| 5004 | ... |

Порт 8080 зарезервирован за Shell Dev Server.

### 3.3 Создание структуры

```bash
SERVICE_ID="your-service-id"
SERVICE_PORT=5003

mkdir -p services/${SERVICE_ID}/{frontend,backend/app}

touch services/${SERVICE_ID}/manifest.json
touch services/${SERVICE_ID}/component.js
touch services/${SERVICE_ID}/Dockerfile
touch services/${SERVICE_ID}/README.md
touch services/${SERVICE_ID}/frontend/index.html
touch services/${SERVICE_ID}/backend/{app.py,wsgi.py,gunicorn.conf.py}
touch services/${SERVICE_ID}/backend/requirements.txt
touch services/${SERVICE_ID}/backend/.env.example
touch services/${SERVICE_ID}/backend/app/__init__.py
```

---

## 4. Шаг 2 — Манифест (manifest.json)

Манифест — главный контракт между сервисом и Shell App. Оболочка загружает его при инициализации и строит карточку сервиса на основе его полей.

### 4.1 Полная схема

```json
{
  "id": "your-service-id",
  "name": "Название сервиса (кириллица, до 30 символов)",
  "description": "Краткое описание функциональности (до 80 символов)",
  "version": "1.0.0",
  "category": "converters",
  "icon": "📋",
  "component": "component.js",
  "status": "active",
  "accepts": ["application/pdf"],
  "supportsVisionOptions": false,
  "endpoints": {
    "base": "/api/your-service-id",
    "convert": "POST /convert",
    "health": "GET /health"
  },
  "maxFileSize": 52428800,
  "outputType": "file-download",
  "outputMime": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  "features": [
    "Описание возможности 1",
    "Описание возможности 2"
  ]
}
```

### 4.2 Описание полей

| Поле | Тип | Обязательно | Описание |
|------|-----|:-----------:|----------|
| `id` | string | ✅ | Уникальный идентификатор (`kebab-case`), совпадает с именем каталога |
| `name` | string | ✅ | Человекочитаемое название (отображается в карточке) |
| `description` | string | ✅ | Описание для карточки (1-2 строки) |
| `version` | string | ✅ | Семантическое версионирование (semver) |
| `category` | string | ✅ | Категория для фильтрации в сайдбаре (см. ниже) |
| `icon` | string | ✅ | Эмодзи-иконка для карточки |
| `component` | string | ✅ | Путь к JS-файлу Web Component (относительно корня сервиса) |
| `status` | string | ✅ | `"active"` — рабочий, `"planned"` — заглушка (карточка задизейблена) |
| `accepts` | string[] | ✅ | MIME-типы принимаемых файлов |
| `supportsVisionOptions` | boolean | ❌ | `true` — Advanced mode покажет опции LLM Vision |
| `endpoints.base` | string | ✅ | Базовый путь API (через прокси) |
| `endpoints.convert` | string | ✅ | Метод и путь основного эндпоинта |
| `endpoints.health` | string | ✅ | Метод и путь health check |
| `maxFileSize` | number\|string | ❌ | Максимальный размер файла (байты или строка `"50MB"`) |
| `outputType` | string | ❌ | Тип ответа: `"file-download"` или `"json"` |
| `outputMime` | string | ❌ | MIME-тип выходного файла |
| `features` | string[] | ❌ | Список возможностей (для Advanced mode) |

### 4.3 Доступные категории

Категории определены в `shell/js/config.js`:

| Значение | Метка в UI | Иконка |
|----------|-----------|--------|
| `converters` | Конвертеры | 🔄 |
| `validation` | Проверка / Нормоконтроль | ✅ |
| `generators` | Генераторы документов | 📄 |

Для добавления новой категории необходимо обновить объект `categories` в `shell/js/config.js`.

---

## 5. Шаг 3 — Backend (Flask API)

### 5.1 Минимальный app.py

```python
"""
@file: app.py
@description: Flask REST API для сервиса {service-name}
@dependencies: flask, flask-cors, python-dotenv
@created: {date}
"""
import os
import uuid
import logging
from pathlib import Path

from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ── Конфигурация ───────────────────────────────────────────────
UPLOAD_FOLDER = Path(os.getenv("UPLOAD_FOLDER", "uploads"))
OUTPUT_FOLDER = Path(os.getenv("OUTPUT_FOLDER", "outputs"))
MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", 50))
PORT = int(os.getenv("PORT", 5003))

UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)
OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)

# ── Flask app ──────────────────────────────────────────────────
app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = MAX_FILE_SIZE_MB * 1024 * 1024

ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:8080").split(",")
ALLOWED_ORIGINS = [origin.strip() for origin in ALLOWED_ORIGINS]
CORS(app, origins=ALLOWED_ORIGINS)


# ── Health Check (обязательно) ─────────────────────────────────
@app.get("/health")
def health():
    return jsonify({
        "status": "ok",
        "service": "your-service-id",
        "version": "1.0.0"
    })


# ── Основной эндпоинт ─────────────────────────────────────────
@app.post("/convert")
def convert():
    # 1. Валидация входных данных
    if "file" not in request.files:
        return jsonify({"error": "Поле 'file' обязательно"}), 400

    file = request.files["file"]
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        return jsonify({"error": "Принимаются только PDF-файлы"}), 400

    # 2. Сохранение временного файла
    job_id = str(uuid.uuid4())
    input_path = UPLOAD_FOLDER / f"{job_id}.pdf"
    file.save(input_path)
    logger.info(f"Processing file: {file.filename}, job_id: {job_id}")

    try:
        # 3. Бизнес-логика (вынесена в отдельный модуль)
        # from app.processor import process
        # result = process(str(input_path))

        # 4. Формирование результата
        output_path = OUTPUT_FOLDER / f"{job_id}.xlsx"
        # build_output(result, str(output_path))

        # 5. Заголовки ответа
        headers = {
            "X-Job-Id": job_id,
        }

        return send_file(
            str(output_path),
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            as_attachment=True,
            download_name=f"result_{job_id}.xlsx",
        ), 200, headers

    except Exception as exc:
        logger.error(f"Error processing: {exc}", exc_info=True)
        error_message = str(exc) if app.debug else "Ошибка обработки файла"
        return jsonify({"error": error_message, "job_id": job_id}), 500

    finally:
        try:
            input_path.unlink(missing_ok=True)
        except Exception as e:
            logger.warning(f"Failed to delete temp file: {e}")


# ── Запуск ─────────────────────────────────────────────────────
if __name__ == "__main__":
    host = os.getenv("FLASK_HOST", "0.0.0.0")
    debug = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    logger.info(f"Starting service on {host}:{PORT}")
    app.run(host=host, port=PORT, debug=debug)
```

### 5.2 wsgi.py (для Gunicorn)

Файл `wsgi.py` решает конфликт имён между модулем `app.py` и пакетом `app/`:

```python
"""
@file: wsgi.py
@description: WSGI точка входа для Gunicorn.
@dependencies: app.py
@created: {date}
"""
import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "_service_main",
    Path(__file__).parent / "app.py"
)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

app = _mod.app
```

### 5.3 gunicorn.conf.py

```python
import os

bind = f"{os.getenv('FLASK_HOST', '0.0.0.0')}:{os.getenv('PORT', '5003')}"
workers = int(os.getenv('GUNICORN_WORKERS', 2))
threads = int(os.getenv('GUNICORN_THREADS', 2))
timeout = int(os.getenv('REQUEST_TIMEOUT_SEC', 120)) + 30
loglevel = os.getenv('LOG_LEVEL', 'info')
accesslog = '-'
errorlog = '-'
worker_class = 'sync'
```

### 5.4 requirements.txt

Базовые зависимости (добавьте специфичные для сервиса):

```
flask>=3.0.0
flask-cors>=4.0.0
python-dotenv>=1.0.0
gunicorn>=22.0.0
```

### 5.5 Организация бизнес-логики

Для простых сервисов вся логика может быть в `app.py`.

Для сложных сервисов вынесите логику в пакет `app/`:

```
backend/
├── app.py          # Только роуты Flask, валидация, оркестрация
└── app/
    ├── __init__.py
    ├── processor.py    # Основная обработка
    ├── validator.py    # Валидация результатов
    └── builder.py      # Формирование выходного файла
```

Каждый модуль в `app/` должен иметь чёткую ответственность (SRP).

---

## 6. Шаг 4 — Web Component (component.js)

Web Component обеспечивает встраивание сервиса в Shell App. Базовый класс `ServiceCard` реализует всю стандартную функциональность (drag-and-drop, health check, прогресс, скачивание файла), поэтому в большинстве случаев кастомный компонент минимален.

### 6.1 Минимальный component.js

```javascript
/**
 * @file: component.js
 * @description: Web Component для сервиса {service-name}.
 * @dependencies: /shell/js/card-grid.js
 * @created: {date}
 */
import { ServiceCard } from '/shell/js/card-grid.js';

class YourServiceCard extends ServiceCard {
  constructor() {
    super();
  }
}

if (!customElements.get('service-card-your-service-id')) {
  customElements.define('service-card-your-service-id', YourServiceCard);
}
```

### 6.2 Именование Custom Element

Тег Custom Element **обязательно** формируется по шаблону:

```
service-card-{service-id}
```

Примеры:
- `service-card-ocr-extractor`
- `service-card-docx-merger`
- `service-card-project-validator`

### 6.3 Кастомизация (при необходимости)

Если стандартное поведение карточки не подходит, можно переопределить методы базового класса:

```javascript
class CustomCard extends ServiceCard {
  constructor() {
    super();
  }

  // Кастомное сообщение после успешной обработки
  // Вызывается из базового #processFileQuick
  // showResult(result) {
  //   super.showResult(result);
  //   this.showMessage('Дополнительная информация', 'success');
  // }
}
```

### 6.4 Как Shell загружает компонент

1. Shell читает `services.json` → получает список id сервисов.
2. Для каждого id параллельно загружает `manifest.json` и `component.js`.
3. `component.js` при загрузке выполняет `customElements.define(...)`.
4. Shell создаёт элемент `<service-card-{id}>` (или базовый `<service-card>`, если кастомный не зарегистрирован).
5. Вызывает `card.setManifest(manifest)` — карточка отрисовывается.

Если `component.js` не найден или содержит ошибку — Shell использует базовый `<service-card>`. Сервис остаётся работоспособным.

---

## 7. Шаг 5 — Standalone-фронтенд

Каждый сервис **обязательно** имеет standalone-версию в `frontend/index.html`. Это позволяет:
- Разрабатывать и тестировать сервис независимо от Shell.
- Демонстрировать функциональность без развёртывания платформы.
- Использовать сервис автономно при необходимости.

### 7.1 Минимальные требования

- Drag-and-drop зона для загрузки файла.
- Индикатор прогресса обработки.
- Отображение результата / кнопка скачивания.
- Сообщения об ошибках.

### 7.2 Стиль

Standalone-фронтенд должен следовать визуальному стилю платформы:

```css
/* Основные цвета платформы */
--bg-gradient: linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%);
--card-bg: rgba(28, 28, 46, 0.96);
--card-border: rgba(255, 255, 255, 0.08);
--text-primary: #eeeef8;
--text-secondary: #8888aa;
--accent: #6366f1;
--accent-hover: rgba(99, 102, 241, 0.28);
--success: #22c55e;
--error: #ef4444;
--warning: #f59e0b;
--border-radius: 16px;
```

### 7.3 API-запросы в standalone-режиме

В standalone-режиме запросы идут напрямую к бэкенду (без прокси Shell):

```javascript
// Standalone: прямой запрос к бэкенду
const API_BASE = window.location.port === '8080'
  ? '/api/your-service-id'   // Через Shell прокси
  : '';                        // Прямой доступ (standalone)

const response = await fetch(`${API_BASE}/convert`, {
  method: 'POST',
  body: formData
});
```

---

## 8. Шаг 6 — Docker

### 8.1 Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Системные зависимости (добавьте специфичные для сервиса)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ backend/

RUN mkdir -p backend/uploads backend/outputs

EXPOSE 5003

CMD ["gunicorn", "-c", "backend/gunicorn.conf.py", "backend.wsgi:app"]
```

### 8.2 Рекомендации

- Базовый образ: `python:3.11-slim` (единый для всех сервисов).
- Системные зависимости: устанавливайте только необходимые.
- Размер файлов: `backend/uploads/` и `backend/outputs/` не попадают в образ (только создаются как пустые).
- `.dockerignore` в корне сервиса:

```
__pycache__
*.pyc
.env
venv/
backend/uploads/
backend/outputs/
.git
```

---

## 9. Шаг 7 — Регистрация в платформе

Для подключения сервиса к Shell необходимо выполнить три действия:

### 9.1 Добавить id в services.json

Файл: `shell/services.json`

```json
{
  "services": [
    "spec-converterv2",
    "invoice-extractor",
    "your-service-id"
  ]
}
```

### 9.2 Добавить прокси-маршрут в dev_server.py

Файл: `dev_server.py` (корень проекта)

Добавить константы:

```python
YOUR_SERVICE_PREFIX = "/api/your-service-id"
YOUR_SERVICE_BACKEND = "http://127.0.0.1:5003"
```

Добавить обработку в `do_GET` и `do_POST`:

```python
elif self.path.startswith(YOUR_SERVICE_PREFIX):
    self._proxy_request("GET", YOUR_SERVICE_PREFIX, YOUR_SERVICE_BACKEND)
```

### 9.3 (Опционально) Настроить systemd unit

Для автозапуска при загрузке WSL2 создайте файл:

`~/.config/systemd/user/your-service-id.service`

```ini
[Unit]
Description=Your Service Name
After=network.target

[Service]
Type=simple
WorkingDirectory=/home/{user}/projects/extraction_specific_PDF/services/your-service-id/backend
ExecStart=/home/{user}/projects/extraction_specific_PDF/services/your-service-id/backend/venv/bin/gunicorn -c gunicorn.conf.py wsgi:app
Restart=on-failure
RestartSec=5
Environment=PATH=/home/{user}/projects/extraction_specific_PDF/services/your-service-id/backend/venv/bin:/usr/bin

[Install]
WantedBy=default.target
```

Активация:

```bash
systemctl --user daemon-reload
systemctl --user enable your-service-id
systemctl --user start your-service-id
systemctl --user status your-service-id
```

---

## 10. Шаг 8 — Запуск и отладка

### 10.1 Ручной запуск бэкенда

```bash
cd services/your-service-id/backend

# Создание виртуального окружения
python3 -m venv venv
source venv/bin/activate

# Установка зависимостей
pip install -r requirements.txt

# Копирование и заполнение конфигурации
cp .env.example .env
# отредактировать .env

# Запуск (dev)
python app.py

# Запуск (production-like)
gunicorn -c gunicorn.conf.py wsgi:app
```

### 10.2 Проверка health check

```bash
curl http://localhost:5003/health
# Ожидаемый ответ: {"service":"your-service-id","status":"ok","version":"1.0.0"}
```

### 10.3 Тестирование через Shell

1. Запустите бэкенд сервиса (порт 5003).
2. Запустите Shell Dev Server (порт 8080):
   ```bash
   cd /path/to/project-root
   python3 dev_server.py
   ```
3. Откройте `http://localhost:8080` в браузере.
4. Карточка сервиса должна появиться в сетке с зелёным индикатором «Онлайн».

### 10.4 Тестирование standalone

```bash
# Откройте в браузере standalone-версию через dev-server:
# http://localhost:8080/services/your-service-id/frontend/index.html

# Или запустите бэкенд отдельно и откройте frontend/index.html напрямую
```

### 10.5 Отладка типичных проблем

| Симптом | Причина | Решение |
|---------|---------|---------|
| Карточка не появляется | id не в `services.json` | Добавить id в `shell/services.json` |
| Карточка «Офлайн» | Бэкенд не запущен или неверный порт | Проверить `curl localhost:{port}/health` |
| HTTP 502 при конвертации | Прокси-маршрут не настроен | Добавить маршрут в `dev_server.py` |
| Кириллица в заголовках → 502 | HTTP-заголовки допускают только ASCII | URL-encode через `urllib.parse.quote()` |
| Правки `component.js` не видны | Кеширование ES-модулей в браузере | Hard reload (`Ctrl+Shift+R`) |
| CORS-ошибки | `ALLOWED_ORIGINS` не включает origin | Проверить `.env` → `ALLOWED_ORIGINS` |

---

## 11. API-контракт

### 11.1 Обязательные эндпоинты

Каждый сервис **обязан** реализовать два эндпоинта:

#### GET /health

```json
{
  "status": "ok",
  "service": "your-service-id",
  "version": "1.0.0"
}
```

Shell опрашивает `/health` каждые 30 секунд. Таймаут: 5 секунд.

#### POST /convert

- **Вход:** `multipart/form-data` с полем `file`.
- **Выход (успех):** файл (бинарный) или JSON.
- **Выход (ошибка):** `{"error": "Описание ошибки"}` с соответствующим HTTP-кодом.

### 11.2 Формат ошибок

Единый формат для всех ошибок:

```json
{
  "error": "Человекочитаемое описание ошибки",
  "code": "ERROR_CODE",
  "job_id": "uuid"
}
```

HTTP-коды:

| Код | Когда |
|-----|-------|
| 400 | Невалидные входные данные (нет файла, неверный формат) |
| 413 | Файл превышает допустимый размер |
| 422 | Файл валиден, но не удалось извлечь данные |
| 500 | Внутренняя ошибка сервера |

### 11.3 Пользовательские заголовки ответа

Для передачи метаданных о результате используйте заголовки с префиксом `X-`:

```python
headers = {
    "X-Job-Id": job_id,
    "X-Vision-Fallback": "false",        # если сервис использует LLM
    "X-Parse-Quality": "ok",              # ok | partial
    "X-Document-Type": "invoice",         # тип обработанного документа
}
```

Shell App читает `X-Vision-Fallback` для отображения badge «Vision».

> **Важно:** значения заголовков — только ASCII. Для кириллицы используйте URL-encoding (`urllib.parse.quote`).

---

## 12. Переменные окружения

### 12.1 Шаблон .env.example

```bash
# Настройки сервера
FLASK_HOST=0.0.0.0
PORT=5003
FLASK_DEBUG=false

# CORS: разрешённые origins (через запятую)
ALLOWED_ORIGINS=http://localhost:8080

# Ограничения
MAX_FILE_SIZE_MB=50
REQUEST_TIMEOUT_SEC=120

# Папки
UPLOAD_FOLDER=uploads
OUTPUT_FOLDER=outputs

# Gunicorn
GUNICORN_WORKERS=2
GUNICORN_THREADS=2
LOG_LEVEL=info

# LLM (если сервис использует)
# LLM_PROVIDER=anthropic
# ANTHROPIC_API_KEY=sk-ant-...
# OPENAI_API_KEY=sk-...
# OPENROUTER_API_KEY=sk-or-...
```

### 12.2 Правила работы с секретами

- **Никогда** не коммитьте `.env` с реальными ключами.
- `.env` добавлен в `.gitignore` на уровне проекта.
- В репозиторий коммитится только `.env.example` с плейсхолдерами.
- В production секреты передаются через переменные окружения Docker/systemd.

---

## 13. Безопасность

### 13.1 Обязательные меры

| Мера | Реализация |
|------|------------|
| **Валидация файлов** | Проверка расширения, MIME-типа, размера |
| **Ограничение размера** | `app.config["MAX_CONTENT_LENGTH"]` в Flask |
| **CORS** | `flask-cors` с явным списком `ALLOWED_ORIGINS` |
| **Удаление временных файлов** | `finally` блок после обработки |
| **Валидация путей** | Запрет `..` и path traversal при работе с файлами |
| **Скрытие деталей ошибок** | В production возвращать общие сообщения, детали — в логи |
| **Секреты** | `.env` в `.gitignore`, `.env.example` без реальных ключей |

### 13.2 Шаблон валидации файла

```python
import magic  # python-magic (опционально)

ALLOWED_EXTENSIONS = {'.pdf'}
ALLOWED_MIMETYPES = {'application/pdf'}
MAX_FILENAME_LENGTH = 255

def validate_upload(file):
    if not file or not file.filename:
        return "Файл не предоставлен"

    filename = file.filename.strip()
    if len(filename) > MAX_FILENAME_LENGTH:
        return "Слишком длинное имя файла"

    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        return f"Недопустимый тип файла: {ext}"

    # Опционально: проверка magic bytes
    # header = file.read(8)
    # file.seek(0)
    # if not header.startswith(b'%PDF'):
    #     return "Файл не является валидным PDF"

    return None
```

### 13.3 Валидация путей

```python
from pathlib import Path

def safe_path(base_dir: Path, filename: str) -> Path:
    """Защита от path traversal."""
    safe = (base_dir / filename).resolve()
    if not str(safe).startswith(str(base_dir.resolve())):
        raise ValueError("Path traversal detected")
    return safe
```

---

## 14. Тестирование

### 14.1 Структура тестов

```
backend/
├── tests/
│   ├── __init__.py
│   ├── test_health.py          # Health check
│   ├── test_convert.py         # Основной эндпоинт
│   ├── test_processor.py       # Бизнес-логика
│   └── fixtures/
│       └── sample.pdf          # Тестовый файл
```

### 14.2 Минимальный набор тестов

```python
import pytest
from app import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_health(client):
    resp = client.get('/health')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['status'] == 'ok'

def test_convert_no_file(client):
    resp = client.post('/convert')
    assert resp.status_code == 400

def test_convert_wrong_type(client):
    from io import BytesIO
    data = {'file': (BytesIO(b'not a pdf'), 'test.txt')}
    resp = client.post('/convert', data=data, content_type='multipart/form-data')
    assert resp.status_code == 400
```

### 14.3 Snapshot-тестирование (для сервисов обработки данных)

- Папка `tests/gold_standard/` с парами `input.pdf` / `expected.json`.
- Тест сравнивает выход обработчика с эталоном.
- Порог прохождения: совпадение > 95%.

---

## 15. Стандарты кода

### 15.1 Python

| Правило | Стандарт |
|---------|----------|
| Стиль | PEP 8 |
| Именование | `snake_case` для функций/переменных, `PascalCase` для классов |
| Строки | Одинарные кавычки для строк, тройные двойные для docstrings |
| Типизация | Type hints для параметров функций и возвращаемых значений |
| Импорты | Группировка: stdlib → сторонние → локальные |
| Логирование | Модуль `logging`, не `print()` |

### 15.2 JavaScript

| Правило | Стандарт |
|---------|----------|
| Переменные | `camelCase` |
| Классы | `PascalCase` |
| Константы | `UPPER_SNAKE_CASE` |
| Модули | ES Modules (`import`/`export`) |
| DOM | Shadow DOM для изоляции стилей |

### 15.3 CSS

| Правило | Стандарт |
|---------|----------|
| Методология | BEM (`block__element--modifier`) |
| Единицы | `rem` для шрифтов, `px` для мелких элементов |
| Цвета | CSS Custom Properties |

### 15.4 Git

| Правило | Формат |
|---------|--------|
| Ветки | `feature/{service-id}/{description}`, `fix/{service-id}/{description}` |
| Коммиты | Conventional Commits: `feat:`, `fix:`, `docs:`, `chore:`, `refactor:` |
| .gitignore | `.env`, `venv/`, `__pycache__/`, `uploads/`, `outputs/` |

### 15.5 Заголовки файлов

Каждый новый файл начинается с заголовка:

**Python:**
```python
"""
@file: filename.py
@description: Краткое описание
@dependencies: связанные модули
@created: YYYY-MM-DD
"""
```

**JavaScript:**
```javascript
/**
 * @file: filename.js
 * @description: Краткое описание
 * @dependencies: связанные модули
 * @created: YYYY-MM-DD
 */
```

---

## 16. Чеклист перед релизом

### Файлы и структура

- [ ] Каталог `services/{service-id}/` соответствует стандартной структуре
- [ ] `manifest.json` содержит все обязательные поля
- [ ] `component.js` регистрирует `service-card-{service-id}`
- [ ] `frontend/index.html` работает автономно
- [ ] `Dockerfile` собирается без ошибок
- [ ] `.env.example` содержит все переменные (без секретов)
- [ ] `requirements.txt` с закреплёнными минимальными версиями
- [ ] `README.md` описывает сервис, установку, API

### API

- [ ] `GET /health` возвращает `{"status": "ok", ...}`
- [ ] `POST /convert` принимает файл и возвращает результат
- [ ] Ошибки возвращаются в формате `{"error": "..."}` с HTTP-кодом
- [ ] Кириллица в заголовках URL-encoded

### Безопасность

- [ ] Валидация типа и размера файлов
- [ ] CORS ограничен `ALLOWED_ORIGINS`
- [ ] Временные файлы удаляются после обработки
- [ ] Нет path traversal уязвимостей
- [ ] Секреты не попадают в репозиторий
- [ ] В production скрыты детали ошибок

### Интеграция

- [ ] id добавлен в `shell/services.json`
- [ ] Прокси-маршрут добавлен в `dev_server.py`
- [ ] Карточка отображается в Shell App
- [ ] Health check показывает «Онлайн»
- [ ] Drag-and-drop работает (Quick mode)
- [ ] Файл скачивается после обработки

### Тесты

- [ ] Health check тест проходит
- [ ] Тест на отсутствие файла (400)
- [ ] Тест на неверный формат файла (400)
- [ ] Тест на успешную обработку (200)

---

## 17. Примеры из существующих сервисов

### spec-converterv2

- Каталог: `services/spec-converterv2/`
- Порт: 5001
- Бизнес-логика: в отдельных модулях `pdf_text_extractor.py`, `spec_utils.py`
- Особенности: Vision fallback для сканов, маппинг колонок, кодировка CP1251

### invoice-extractor

- Каталог: `services/invoice-extractor/`
- Порт: 5002
- Бизнес-логика: пакет `app/` (`extractor.py`, `llm_client.py`, `excel_builder.py`, `validators.py`, `normalizer.py`)
- Особенности: Vision-режим по выбору, валидация данных, нормализация, кастомные заголовки ответа

Оба сервиса можно использовать как справочные реализации при создании нового микросервиса.

---

## 18. FAQ

**Q: Можно ли использовать другой язык/фреймворк вместо Python/Flask?**  
A: Да. Архитектура позволяет любой стек (Node.js, Go и т.д.), при условии соблюдения API-контракта (`GET /health`, `POST /convert`) и предоставления `manifest.json`, `component.js`, `Dockerfile`. Однако рекомендуется придерживаться Python/Flask для единообразия.

**Q: Где хранить вспомогательные файлы (шаблоны, конфиги парсинга)?**  
A: В каталоге `backend/` сервиса. Для статических ресурсов — `backend/static/` или `backend/data/`.

**Q: Как добавить новую категорию в сайдбар?**  
A: Отредактировать `shell/js/config.js` → объект `CONFIG.categories`.

**Q: Нужна ли база данных?**  
A: Платформа stateless — постоянное хранилище не предусмотрено. Если сервису нужна БД (SQLite, PostgreSQL), она развёртывается изолированно внутри сервиса.

**Q: Как обрабатывать длительные операции?**  
A: Сейчас все запросы синхронные. При необходимости: вернуть `job_id` и статус 202, реализовать `GET /status/{job_id}` для polling. В будущем планируется Celery + Redis для Task Queue.

**Q: Как тестировать без LLM API-ключей?**  
A: Создайте mock-режим в коде обработчика, который возвращает фиксированный результат. Управляйте им через переменную окружения (`MOCK_MODE=true`).

**Q: Куда класть документацию?**  
A: Каждый сервис содержит `README.md`. Общая документация — в `/docs/`. API описывается в `manifest.json` и docstrings в `app.py`.

---

*Документ обновляется при изменении архитектуры платформы или внедрении новых стандартов.*
