# Task Tracker — Extraction Specific PDF

> **Обновлено:** 2026-04-20
> **Приоритеты:** Критический / Высокий / Средний / Низкий

---

## Задача: ODOO-002 — Odoo purchase.order (invoice-extractor)
- **Статус**: Завершена
- **Описание**: Режим `odoo_po_xlsx` в `POST /convert`, модуль `po_builder.py`, кнопка в `component.js`, тесты `test_po_builder.py`, документация в `docs/changelog.md`, `docs/project.md`, `docs/tasktreckerodoo.md`.
- **Шаги выполнения**:
  - [x] Интеграция в `app.py` и очистка временного файла
  - [x] Обновление UI переключателя режимов
  - [x] Документация и changelog
- **Зависимости**: ODOO-001 (odoo_xlsx)

---

## Фаза 1 — Оболочка и интеграция (MVP)

### Задача: Проектирование архитектуры платформы
- **Статус**: Завершена
- **Приоритет**: Критический
- **Описание**: Разработка архитектурного документа, определение структуры оболочки, формата манифеста, стандартов для микросервисов.
- **Шаги выполнения**:
  - [x] Анализ существующего кода spec-converterv2
  - [x] Определение архитектуры оболочки (Shell App)
  - [x] Определение формата манифеста сервиса
  - [x] Документирование стандартов для микросервисов
  - [x] Создание project.md
- **Зависимости**: Нет

---

### Задача: Создание Shell App (оболочка)
- **Статус**: Завершена
- **Приоритет**: Критический
- **Описание**: Разработка единого веб-интерфейса на Vanilla JS + Web Components. Сетка карточек 3×N, сайдбар с категориями, dual-mode drag-and-drop (Quick + Advanced).
- **Шаги выполнения**:
  - [x] Выбор UI-фреймворка → **Vanilla JS + Custom Elements (Shadow DOM)**
  - [x] Создание структуры директории `shell/`
  - [x] Верстка макета: header, sidebar, grid (CSS Grid + Custom Properties)
  - [x] Реализация CSS Grid сетки карточек (3 в ряд, ≥ 6 на экран)
  - [x] Реализация базового Custom Element `<service-card>` (Shadow DOM)
  - [x] Реализация сайдбара с категориями (Конвертеры, Проверка/Нормоконтроль, Генераторы)
  - [x] Quick mode: drag-and-drop файла на карточку → обработка с дефолтными настройками
  - [x] Advanced mode: клик → модалка `<dialog>` с логами, выбором провайдера
  - [x] Индикатор статуса сервиса (online/offline через `/health`)
  - [x] Badges: 👁 (Vision fallback), красная подсветка (ошибка)
  - [x] История операций в `localStorage` (последние 10)
  - [x] Адаптивная верстка (3→2→1 колонки)
- **Файлы**: `shell/index.html`, `shell/css/styles.css`, `shell/js/{app,config,card-grid,service-registry,sidebar,history,modal}.js`
- **Зависимости**: Формат манифеста (завершено)

---

### Задача: Service Registry — реестр сервисов
- **Статус**: Завершена
- **Приоритет**: Критический
- **Описание**: Механизм загрузки манифестов и JS-компонентов сервисов, динамическое построение карточек через Custom Elements.
- **Шаги выполнения**:
  - [x] Создание `services/spec-converterv2/manifest.json`
  - [x] Реализация `service-registry.js` — сканирование `services/*/manifest.json`, загрузка `component.js`
  - [x] Динамическое создание Custom Elements `<service-card-{id}>` из реестра
  - [x] Группировка карточек по категориям (Конвертеры, Проверка, Генераторы)
  - [x] Health-check опрос сервисов (polling `/health`)
- **Файлы**: `shell/js/service-registry.js`, `shell/js/card-grid.js`, `services/spec-converterv2/component.js`
- **Зависимости**: Shell App (базовая верстка)

---

### Задача: Интеграция spec-converterv2 в оболочку (Dual mode)
- **Статус**: Завершена
- **Приоритет**: Высокий
- **Описание**: Адаптация существующего сервиса: создание Web Component, сохранение `index.html` для standalone-режима, переход на `.env` для API-ключей.
- **Шаги выполнения**:
  - [x] Создание `services/spec-converterv2/manifest.json`
  - [x] Создание `services/spec-converterv2/component.js` — Web Component (Custom Element) с fetch-перехватчиком для X-Sheet-Names
  - [x] Сохранение `services/spec-converterv2/frontend/index.html` для standalone-тестирования
  - [x] Адаптация API-путей для path-based routing через Gateway (base: `/api/spec-converter`, порт 5001)
  - [x] Переход с `config.py` на `.env` + `python-dotenv` для API-ключей
  - [x] Обработка ошибок: badges 👁 (vision via `X-Vision-Fallback`), красная подсветка (ошибка через базовый `ServiceCard`)
  - [x] Кнопка «Только Vision» в Advanced mode (параметр `vision_only` поддержан в `app.py`)
  - [x] Тестирование конвертации через оболочку (Quick + Advanced mode) — ручное тестирование
- **Файлы**: `services/spec-converterv2/backend/{app.py,spec_utils.py,pdf_text_extractor.py,requirements.txt,.env.example}`, `services/spec-converterv2/frontend/index.html`, `services/spec-converterv2/component.js`
- **Зависимости**: Shell App, Service Registry

---

### Задача: Настройка Nginx (API Gateway, path-based)
- **Статус**: Завершена
- **Приоритет**: Высокий
- **Описание**: Конфигурация Nginx как reverse proxy. Path-based routing: `localhost/` → Shell, `/api/spec-converter/` → Flask :5001, `/api/invoice-extractor/` → Flask :5002. Выполнено в рамках FIX-008.
- **Шаги выполнения**:
  - [x] Создание `gateway/nginx.conf`
  - [x] Настройка маршрутов: `location /` → Shell, `location /api/spec-converter/` → `:5001`, `location /api/invoice-extractor/` → `:5002`
  - [x] Убраны CORS-заголовки из Flask-сервисов (flask-cors удалён), CORS управляется на уровне Gateway
  - [x] Настройка rate limiting (`limit_req_zone`, 10r/s burst=20)
  - [x] Настройка ограничения размера файлов (`client_max_body_size 50M`)
  - [x] Настройка таймаутов для длительных операций (`proxy_read_timeout 180s`)
  - [x] Production systemd-юниты в `gateway/systemd/`
- **Файлы**: `gateway/nginx.conf`, `gateway/systemd/*.service`
- **Зависимости**: Shell App, spec-converterv2, invoice-extractor

---

### Задача: Настройка автозапуска сервисов (systemd)
- **Статус**: Завершена
- **Приоритет**: Высокий
- **Описание**: Все три сервиса платформы переведены на автозапуск через systemd user-units, чтобы после перезагрузки WSL2 не требовался ручной старт. Обнаружен и исправлен конфликт имён `app.py` vs пакет `app/` в invoice-extractor.
- **Шаги выполнения**:
  - [x] Создать `.env` для invoice-extractor (text-only режим, без LLM-ключей)
  - [x] Исправить `gunicorn.conf.py`: несоответствие переменных `PORT` vs `FLASK_PORT`
  - [x] Создать `wsgi.py` — WSGI-точка входа для gunicorn (обход конфликта `app.py` / `app/`)
  - [x] Создать `~/.config/systemd/user/invoice-extractor.service`
  - [x] Создать `~/.config/systemd/user/spec-converterv2.service`
  - [x] Создать `~/.config/systemd/user/docplatform-dev.service`
  - [x] `systemctl --user enable` все три сервиса
  - [x] `loginctl enable-linger serg45` — запуск user-units при загрузке системы без логина
  - [x] Проверка health-эндпоинтов после запуска
- **Файлы**: `services/invoice-extractor/backend/{.env,wsgi.py,gunicorn.conf.py}`, `~/.config/systemd/user/*.service`
- **Зависимости**: invoice-extractor, spec-converterv2, dev_server

---

### Задача: Внедрение микросервиса invoice-extractor
- **Статус**: Завершена
- **Приоритет**: Высокий
- **Описание**: Разработка и интеграция микросервиса для парсинга PDF-счетов поставщиков с извлечением структурированных данных в Excel. Поддержка LLM Vision для сложных/отсканированных документов.
- **Выполненные шаги**:
  - [x] INV-001: Проектирование архитектуры парсера счетов
  - [x] INV-002: Реализация text-first пайплайна (pdfplumber)
  - [x] INV-003: Интеграция с LLM (Anthropic, OpenAI, OpenRouter)
  - [x] INV-004: Валидация и нормализация извлечённых данных
  - [x] INV-005: Генератор XLSX с форматированием
  - [x] INV-006: Web Component для встраивания в Shell
  - [x] INV-007: Манифест и регистрация в Service Registry
  - [x] INV-008: API endpoints: /health, /convert с параметрами (vision_only, provider, output)
  - [x] INV-009: Обновление документации проекта
  - [x] INV-010: Интеграция прокси-маршрутов в dev_server.py
- **Зависимости**: Shell App, Service Registry

---

## Фаза 1.5 — Исправления по Code Review (2026-03-17)

> Все 13 задач выявлены в ходе code review. Статусы актуальны на 2026-03-17.

### FIX-001: Утечка секретов и мёртвый код ✅
- **Статус**: Завершена
- **Приоритет**: Критический
- **Описание**: Удаление backup-файлов с импортами `config.py`; проверка Git-истории на наличие секретов.
- **Шаги выполнения**:
  - [x] Проверить Git-историю — реальных ключей не найдено, ротация не требуется
  - [x] Удалены мёртвые файлы: `app_anthropic_only.py.backup`, `app_openrouter.py`, все `config*.example`
  - [x] `.gitignore` уже содержал `*.backup`, `*.bak`, `config*.py`, `config*.example`
  - [x] `.env` файлы обоих сервисов в `.gitignore` (`**/backend/.env`)

---

### FIX-002: CORS без ограничений в spec-converterv2 ✅
- **Статус**: Завершена (частично — FIX-002.3 требует ручной правки на сервере)
- **Приоритет**: Критический
- **Описание**: `CORS(app)` без origins → `CORS(app, origins=ALLOWED_ORIGINS)`. После FIX-008 (Nginx gateway) flask-cors полностью удалён из обоих сервисов — CORS управляется на уровне proxy.
- **Шаги выполнения**:
  - [x] Добавлен `ALLOWED_ORIGINS` в `.env.example` spec-converterv2
  - [x] `app.py` обновлён — ограниченный CORS
  - [x] flask-cors удалён из обоих сервисов (FIX-008) — CORS через gateway
  - [ ] **FIX-002.3** — Обновить `.env` на production-сервере с актуальными origins *(ручная задача)*

---

### FIX-003: Нет валидации содержимого файлов ✅
- **Статус**: Завершена
- **Приоритет**: Критический
- **Описание**: Оба сервиса проверяли только расширение. Добавлена проверка magic bytes (`%PDF-`) и ограничение размера.
- **Шаги выполнения**:
  - [x] `python-magic` добавлен в `requirements.txt` обоих сервисов
  - [x] Утилиты `_validate_pdf()` созданы в обоих `app.py`
  - [x] `MAX_CONTENT_LENGTH = 50 MB` добавлен в spec-converterv2

---

### FIX-004: Race condition и потеря кириллицы при сохранении файлов ✅
- **Статус**: Завершена
- **Приоритет**: Высокий
- **Описание**: `secure_filename("Спецификация.pdf")` → `"_2.pdf"`. Заменено на UUID-префикс + safe имя.
- **Шаги выполнения**:
  - [x] `_safe_filename()` создана в spec-converterv2: `{uuid[:12]}_{safe_base}.pdf`
  - [x] invoice-extractor уже использовал UUID — проверено, оставлено без изменений
  - [x] Оригинальное имя сохраняется в `download_name` ответа

---

### FIX-005: Отсутствие таймаутов на внешние API-вызовы ✅
- **Статус**: Завершена
- **Приоритет**: Высокий
- **Описание**: Vision-вызовы без явного HTTP-таймаута → воркер Gunicorn блокируется при зависании API провайдера.
- **Шаги выполнения**:
  - [x] `REQUEST_TIMEOUT_SEC=120` добавлен в `.env.example` обоих сервисов
  - [x] spec-converterv2: таймауты добавлены в Anthropic/OpenAI/OpenRouter клиенты
  - [x] invoice-extractor: уже использовал `TIMEOUT = int(os.getenv("REQUEST_TIMEOUT_SEC", 120))`

---

### FIX-006: `print()` вместо `logging` в spec-converterv2 ✅
- **Статус**: Завершена
- **Приоритет**: Высокий
- **Описание**: 28 `print()` заменены на `logger.info/warning/error/exception`.
- **Шаги выполнения**:
  - [x] Настройка `logging.basicConfig` + `logger = logging.getLogger(__name__)`
  - [x] Все `print()` в `app.py` и `pdf_text_extractor.py` заменены на logging
  - [x] `PYTHONUNBUFFERED=1` добавлен в `.env.example`

---

### FIX-007: Дублирование LLM-клиента между сервисами ✅
- **Статус**: Завершена
- **Приоритет**: Высокий
- **Описание**: Инфраструктурный код Anthropic/OpenAI/OpenRouter вынесен в общий пакет `shared/llm_client/`.
- **Шаги выполнения**:
  - [x] Создан `shared/llm_client/` как installable package (`pyproject.toml`, `pip install -e`)
  - [x] `call_vision_llm(images, prompt, provider, ...)` — единая точка входа для всех провайдеров
  - [x] `pdf_to_images()`, `parse_json_response()` вынесены в `shared/llm_client/vision.py`
  - [x] invoice-extractor: `app/llm_client.py` — тонкая обёртка над shared
  - [x] spec-converterv2: убраны ~105 строк дублирующего кода
  - [x] `requirements.txt` обоих сервисов: `-e ../../../shared/llm_client`
- **Файлы**: `shared/llm_client/`, `services/*/backend/requirements.txt`

---

### FIX-008: Nginx Gateway ✅
- **Статус**: Завершена
- **Приоритет**: Высокий
- **Описание**: Production-готовый Nginx gateway с rate limiting, gzip, 50MB лимит, 180s таймаут для LLM. spec-converterv2 переведён на gunicorn. flask-cors удалён из обоих сервисов.
- **Шаги выполнения**:
  - [x] `gateway/nginx.conf`: rate limiting 10r/s burst=20, gzip, upstreams :5001/:5002
  - [x] flask-cors удалён из обоих сервисов (CORS через gateway)
  - [x] `services/spec-converterv2/backend/wsgi.py` и `gunicorn.conf.py` созданы
  - [x] Production systemd-юниты: `gateway/systemd/{nginx,spec-converterv2,invoice-extractor}.service`
  - [x] `~/.config/systemd/user/spec-converterv2.service` обновлён на gunicorn
  - [x] `dev_server.py`: добавлено предупреждение [DEV] о production-использовании Nginx
- **Файлы**: `gateway/nginx.conf`, `gateway/systemd/`, `services/spec-converterv2/backend/{wsgi.py,gunicorn.conf.py}`

---

### FIX-009: Отсутствие автоматических тестов ✅
- **Статус**: Завершена
- **Приоритет**: Высокий
- **Итог**: **126 тестов** (62 invoice-extractor + 64 spec-converterv2), все проходят.
- **Шаги выполнения**:
  - [x] `services/spec-converterv2/backend/tests/`: conftest, test_health, test_convert_api, test_validation, test_text_extractor
  - [x] `services/invoice-extractor/backend/tests/`: conftest, test_health, test_convert_api, test_validators, test_normalizer
  - [x] Исправлен баг в `validators.py`: `qty×price` сравнивалось с `amount_w_vat` вместо `amount_wo_vat`
  - [x] `pytest>=8.0.0`, `pytest-cov>=5.0.0` добавлены в `requirements.txt` обоих сервисов
  - [x] `Makefile` в корне: `make test`, `make test-spec`, `make test-invoice`, `make lint`, `make format`
- **Файлы**: `services/*/backend/tests/`, `Makefile`

---

### FIX-010: Нет CI/CD ✅
- **Статус**: Завершена (деплой-шаг не реализован — опционально)
- **Приоритет**: Средний
- **Шаги выполнения**:
  - [x] `.github/workflows/ci.yml`: jobs `test` (Python 3.11, libmagic1, shared llm_client, раздельные прогоны) + `lint` (ruff)
  - [x] `ruff.toml`: `line-length=120`, `target-version="py311"`
  - [ ] Деплой через SSH или Docker push *(опционально)*
- **Файлы**: `.github/workflows/ci.yml`, `ruff.toml`

---

### FIX-011: Жёстко зашитые порты ✅
- **Статус**: Завершена
- **Приоритет**: Низкий
- **Шаги выполнения**:
  - [x] `.env.example` в корне: `SHELL_PORT`, `SPEC_CONVERTER_PORT`, `INVOICE_EXTRACTOR_PORT`
  - [x] `dev_server.py`: читает порты из `.env` через `python-dotenv` (fallback на defaults 8080/5001/5002)
  - [x] `shell/js/config.js` уже использует относительные пути — изменений не потребовалось

---

### FIX-012: Health endpoint — утечка информации ✅
- **Статус**: Завершена
- **Приоритет**: Низкий
- **Шаги выполнения**:
  - [x] `GET /health` → только `{status, service, version}`
  - [x] `GET /health/details` → полная инфо, но доступен только с `127.0.0.1`/`::1` (иначе 403)
- **Файлы**: `services/spec-converterv2/backend/app.py`

---

### FIX-013: Консолидация документации spec-converterv2 ✅
- **Статус**: Завершена
- **Приоритет**: Низкий
- **Описание**: Все хаотичные файлы (`README.md`, `QUICKSTART.md`, `OPENROUTER_GUIDE.md`, `WSL_DNS_FIX.md`, `ИСПРАВЛЕНИЕ.md`, `TEXT_FIRST_PIPELINE.md`, `switch_provider.sh`, `start.sh`) были удалены в FIX-001. Сервис содержит только `backend/`, `frontend/`, `manifest.json`.

---

## Фаза 2 — Контейнеризация и DevOps

### Задача: Контейнеризация сервисов (Docker Compose)
- **Статус**: Не начата
- **Приоритет**: Высокий
- **Описание**: Docker Compose для всего стека. Запуск одной командой `docker-compose up`.
- **Шаги выполнения**:
  - [ ] Dockerfile для services/spec-converterv2 (Python + Gunicorn, 2-4 workers)
  - [ ] Dockerfile для services/invoice-extractor
  - [ ] Dockerfile для Nginx (Shell App + Gateway в одном контейнере)
  - [ ] `docker-compose.yml` для всего стека
  - [ ] Health checks в docker-compose
  - [ ] Cron-задача: удаление временных файлов старше 1 часа
  - [ ] Тестирование полного стека через Docker
- **Зависимости**: Все задачи Фазы 1

---

### Задача: Мониторинг и логирование
- **Статус**: Не начата
- **Приоритет**: Средний
- **Описание**: Наблюдаемость платформы — метрики, логи, алерты.
- **Шаги выполнения**:
  - [ ] Структурированное логирование в JSON
  - [ ] Prometheus endpoints в сервисах
  - [ ] Grafana дашборд
  - [ ] Алерты на падение сервисов
- **Зависимости**: Контейнеризация

---

## Фаза 3 — Расширение функциональности

### Задача: Task Queue и система прогресса
- **Статус**: Не начата
- **Приоритет**: Средний
- **Описание**: Celery + Redis для фоновых задач. Пользователь загружает файл → получает `task_id` → Shell polling статуса.
- **Шаги выполнения**:
  - [ ] Установка Celery + Redis
  - [ ] Эндпоинт `POST /convert` → возвращает `task_id`
  - [ ] Эндпоинт `GET /task/{id}` → статус и результат
  - [ ] Polling из Shell App (или WebSocket/SSE)
  - [ ] Прогресс-бар в карточке сервиса
  - [ ] Toast-уведомления об ошибках
- **Зависимости**: Shell App, Gateway, Контейнеризация

---

### Задача: Второй микросервис (из роадмапа)
- **Статус**: Не начата
- **Приоритет**: Средний
- **Описание**: Один из: Image-to-Text (OCR), DOCX Merger, Project Validator. Валидация plug-and-play архитектуры.
- **Шаги выполнения**:
  - [ ] Выбор конкретного сервиса из роадмапа
  - [ ] Создание `manifest.json`
  - [ ] Создание `component.js` (Web Component в корне сервиса)
  - [ ] Реализация бэкенда
  - [ ] Dockerfile + добавление в `docker-compose.yml`
  - [ ] Интеграция в оболочку через Service Registry
  - [ ] Тестирование standalone и embedded режимов
- **Зависимости**: Shell App, Service Registry, Gateway

---

## Фаза 4 — Продакшн

### Задача: Безопасность
- **Статус**: В процессе (базовый уровень достигнут в Фазе 1.5)
- **Приоритет**: Высокий
- **Описание**: Аудит и усиление безопасности платформы.
- **Шаги выполнения**:
  - [x] Валидация MIME-типа и magic bytes загружаемых файлов (FIX-003)
  - [x] Защита от path traversal (`validate_folder_path` в invoice-extractor)
  - [x] Переход на `.env` + `python-dotenv` (выполнено)
  - [x] CORS ограничен через gateway (FIX-002, FIX-008)
  - [ ] Content-Security-Policy заголовки
  - [ ] Basic Auth через Nginx (заготовка, включается по потребности)
  - [ ] Аудит зависимостей (`pip audit`)
- **Зависимости**: Все фазы

---

### Задача: Оптимизация производительности
- **Статус**: Не начата
- **Приоритет**: Средний
- **Описание**: Кэширование, параллелизм, нагрузочное тестирование.
- **Шаги выполнения**:
  - [ ] Параллельная обработка страниц PDF
  - [ ] Кэширование результатов (Redis)
  - [ ] Lazy loading карточек в оболочке
  - [ ] Нагрузочное тестирование (Locust / k6)
  - [ ] Профилирование бэкенда
- **Зависимости**: Контейнеризация, Мониторинг

---

## Тестирование

### Задача: Базовые unit/integration тесты
- **Статус**: Завершена (FIX-009)
- **Итог**: 126 тестов (62 invoice-extractor + 64 spec-converterv2). Запуск: `make test`.

---

### Задача: Snapshot Testing для text-first pipeline
- **Статус**: Не начата
- **Приоритет**: Средний
- **Описание**: Эталонный PDF + ожидаемый JSON. Порог прохождения: ≥ 90% совпадений ячеек.
- **Шаги выполнения**:
  - [ ] Создание папки `gold_standard/` с парами `input.pdf` / `expected.json`
  - [ ] Написание скрипта сравнения JSON-выхода с эталоном
  - [ ] Порог прохождения: > 95% совпадений
  - [ ] Интеграция тестов в CI/CD
- **Зависимости**: FIX-009 (инфраструктура тестов — готова)

---

## Существующие задачи (spec-converterv2)

### Задача: Повышение точности text-first пайплайна
- **Статус**: В процессе
- **Приоритет**: Средний
- **Описание**: Текущая точность ~90.6%. Необходимо улучшить маппинг колонок и постобработку для повышения до ≥95%.
- **Шаги выполнения**:
  - [x] Базовый text-first пайплайн
  - [x] Маппинг колонок по нумерации 1-9
  - [x] Исправление кодировки CP1251
  - [x] Фильтрация штампов и рамок
  - [ ] Улучшение порядка строк (основной источник расхождений)
  - [ ] Обработка edge-cases в форматировании
  - [ ] Расширение набора тестовых PDF
- **Зависимости**: Нет

---

*При выполнении задач — обновляй статус. Новые задачи добавляй с приоритетом.*
