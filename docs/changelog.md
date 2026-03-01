# Changelog — Extraction Specific PDF

> Дневник наблюдений проекта. Каждая запись содержит дату, наблюдения, решения и проблемы.  
> Цель: обеспечить бесшовную работу различных разработчиков.

---

## [2026-03-01] — Настроен автозапуск сервисов через systemd

### Добавлено
- `~/.config/systemd/user/invoice-extractor.service` — автозапуск парсера счетов (gunicorn, порт 5002)
- `~/.config/systemd/user/spec-converterv2.service` — автозапуск конвертера спецификаций (порт 5001)
- `~/.config/systemd/user/docplatform-dev.service` — автозапуск dev-сервера (порт 8080)
- `services/invoice-extractor/backend/wsgi.py` — WSGI точка входа для gunicorn (обход конфликта `app.py` vs `app/`)
- `services/invoice-extractor/backend/.env` — конфигурация без LLM (text-only режим)

### Исправлено
- `gunicorn.conf.py`: несоответствие переменных `PORT` и `FLASK_PORT` — теперь читает оба
- Включён `loginctl enable-linger` для запуска user-сервисов при загрузке WSL2 без интерактивного логина

---

## [2026-03-01] — Добавлен микросервис invoice-extractor для парсинга счетов

### Добавлено
- **Микросервис `invoice-extractor`** (порт **5002**) — парсинг PDF-счетов поставщиков с автоматическим извлечением структурированных данных в Excel:
  - Endpoints: `/api/invoice-extractor/health`, `/api/invoice-extractor/convert`
  - Параметры API: `vision_only` (принудить Vision-режим), `provider` (anthropic/openrouter/openai), `output` (json/xlsx/both)
  - Поддержка LLM Vision через Anthropic, OpenAI, OpenRouter для распознавания отсканированных счетов
  - Экспорт структурированных данных в XLSX формат с валидацией
  - Заголовки ответа: `X-Vision-Fallback`, `X-Document-Type`, `X-Parse-Quality`, `X-Job-Id`, `X-Invoice-Number`
- **Web Component `invoice-extractor`** — встраивание в Shell App как service-card с поддержкой drag-and-drop
- **Манифест `services/invoice-extractor/manifest.json`** для регистрации в сервис-реестре
- **Модули Python**: `extractor.py` (парсер), `llm_client.py` (интеграция с LLM), `excel_builder.py` (генератор XLSX), `validators.py`, `normalizer.py`
- **Документация**: `services/invoice-extractor/README.md` с инструкциями запуска, API, конфигурацией, примерами Docker

### Изменено
- **`dev_server.py`** — добавлен прокси для маршрута `/api/invoice-extractor/*` → `http://127.0.0.1:5002/*`
- **`shell/services.json`** — добавлена регистрация микросервиса `invoice-extractor`
- **`docs/project.md`** — обновлена документация:
  - Раздел 3.5: добавлена инструкция запуска бэкенда `invoice-extractor`
  - Раздел 6: добавлено полное описание микросервиса (стек, API, особенности, структура файлов)
  - Раздел 11: обновлена целевая структура проекта со слабой папкой `services/invoice-extractor/`
  - Раздел 13: роадмап обновлён — `invoice-extractor` отмечен как **Реализован**
  - Мета-информация: версия 1.3, дата 2026-03-01
- **Локальная разработка** — теперь поддерживает параллельный запуск spec-converterv2 (5001) и invoice-extractor (5002)

### Примечания
- Text-first пайплайн используется по умолчанию для скорости; Vision-режим включается параметром `vision_only=true` в Advanced mode
- Временные PDF-файлы удаляются автоматически после обработки
- Поддерживается выбор LLM-провайдера через переменную окружения `LLM_PROVIDER` в `.env` или параметром API `provider`

---

### Исправлено
- **Некорректная вёрстка**: Dev-сервер отдавал `/` без редиректа, из‑за чего CSS и JS запрашивались как `/css/...` и `/js/...` (404). Теперь `/` → 302 → `/shell/index.html`, относительные пути работают.
- **Модальное окно видно при загрузке**: Добавлен атрибут `hidden` у `#advanced-modal` и его переключение в `modal.js` — модалка скрыта даже при отсутствии CSS.
- **Ошибка в CSS**: `padding: var(--space-xl) * 2` заменено на `calc(var(--space-xl) * 2)` в `.grid-loading`.
- **HTTP 502 при конвертации**: Flask-бэкенд падал с `UnicodeEncodeError` при отправке кириллических имён листов Excel в заголовке `X-Sheet-Names` (HTTP-заголовки должны быть ASCII/latin-1). Исправлено через URL-encoding (`urllib.parse.quote`) на бэкенде и `decodeURIComponent` на фронтенде (`app.py`, `component.js`, `frontend/index.html`).
- **Чипы листов в карточке показывались в виде `%D0%...`**: Добавлено безопасное декодирование URL-encoded строк при рендере чипов в `services/spec-converterv2/component.js`.
- **Залипание старой версии `component.js` в браузере**: В dev-режиме на localhost добавлен cache-busting query при динамическом `import()` компонентов (`shell/js/service-registry.js`), чтобы гарантированно подтягивались свежие правки без ручной очистки кэша.

---

## [2026-03-01] — Dev-сервер для локальной разработки

### Добавлено
- `dev_server.py` — Python dev-сервер: раздаёт статику из корня, проксирует `/api/spec-converter/*` → `localhost:5001`. Запуск: `python3 dev_server.py` (порт 8080). Требует запущенный Flask backend: `cd services/spec-converterv2/backend && python3 app.py`. Корневой путь `/` перенаправляет на `/shell/index.html`.

---

## [2026-02-18] — Интеграция spec-converterv2 в оболочку (Dual mode)

### Добавлено
- `services/spec-converterv2/backend/app.py` — обновлённый Flask-бэкенд: загрузка конфигурации из `.env` (python-dotenv), заголовки ответа `X-Vision-Fallback` и `X-Sheet-Names`, параметры `vision_only` и `provider` из запроса (Advanced mode), health endpoint соответствует стандарту платформы (`service`, `version`).
- `services/spec-converterv2/backend/requirements.txt` — добавлена зависимость `python-dotenv>=1.0.0`.
- `services/spec-converterv2/backend/.env.example` — шаблон переменных окружения (без секретов).
- `services/spec-converterv2/frontend/index.html` — standalone-режим: drag-and-drop, выбор провайдера, чекбокс «Только Vision», health-check статус, отображение чипов листов Excel, авто-скачивание.
- `services/spec-converterv2/component.js` — расширен: отображение листов Excel (X-Sheet-Names), fetch-перехватчик для чтения заголовков ответа, кастомные сообщения прогресса в Quick mode.

### Изменено
- Конфигурация API-ключей перенесена из `config.py` → `.env` (соответствует Security-стандартам платформы).
- Путь UPLOAD/OUTPUT папок теперь относительный к директории `services/spec-converterv2/` (не к `backend/`).
- Порт бэкенда: `5000` → `5001` (согласно архитектуре: каждый сервис получает свой порт `:500N`).

### Безопасность
- `.env` добавлен в `.gitignore`, в репозитории только `.env.example`.

---

## [2026-02-18] — Service Registry: динамическая загрузка компонентов

### Добавлено
- `services/spec-converterv2/component.js` — Web Component `<service-card-spec-converterv2>`, расширяет базовый `ServiceCard`. Точка расширения для spec-converter-специфичного поведения в будущем.

### Изменено
- `shell/js/service-registry.js` — добавлен метод `#loadComponent(id)`: при инициализации параллельно с загрузкой манифестов загружает `component.js` каждого сервиса через динамический `import()`. Метод `#createCard()` теперь создаёт `<service-card-{id}>` если Custom Element зарегистрирован, иначе — базовый `<service-card>` (graceful fallback).
- `shell/js/card-grid.js` — класс `ServiceCard` экспортируется (`export class ServiceCard`), что позволяет сервисам расширять базовую карточку. `customElements.define('service-card', ...)` защищён от повторной регистрации (`customElements.get` check).

---

## [2026-02-18] — Реализация Shell App (MVP)

### Добавлено
- `shell/` — полная оболочка платформы (SPA): `index.html`, CSS, 7 JS-модулей
- `shell/js/card-grid.js` — Custom Element `<service-card>` с Shadow DOM: drag-and-drop, health check, badges
- `shell/js/service-registry.js` — динамическая загрузка `manifest.json`, фильтрация карточек
- `shell/js/sidebar.js` — навигация по категориям (Конвертеры / Проверка / Генераторы)
- `shell/js/history.js` — история последних 10 операций в localStorage
- `shell/js/modal.js` — Advanced mode: `<dialog>` с логом, провайдером, прогресс-баром
- `shell/js/app.js` — точка входа, связка всех модулей через CustomEvents
- `shell/js/config.js` — конфигурация путей к API и интервалов
- `shell/css/styles.css` — тёмная тема, CSS Grid 3×N → 2×N → 1×N (adaptive), BEM, CSS Custom Properties
- `services/spec-converterv2/manifest.json` — манифест первого сервиса
- `services/{ocr,docx-merger,project-validator}/manifest.json` — placeholder-манифесты
- `shell/services.json` — индекс зарегистрированных сервисов

### Изменено
- Структура проекта: добавлены директории `shell/` и `services/` по целевой архитектуре

---

## [2026-02-18] — Уточнение структуры проекта

### Наблюдения

- Микросервисы находились в корне проекта на одном уровне с `shell/`, `gateway/`, `docs/`, что затрудняло навигацию при росте количества сервисов.

### Решения

- Корень проекта именуется `project-root/`.
- Все микросервисы размещены в единой ветке `services/` (`services/spec-converterv2/`, `services/<service-n>/`).
- Web Component каждого сервиса — `component.js` в корне сервиса (не в `frontend/`).
- Shell App загружает компоненты по пути `/services/{id}/component.js`.

### Проблемы

- Нет (уточнение структуры).

---

### Изменено
- `docs/project.md` → v1.2: структура `project-root/services/`, `component.js`, обновлены Mermaid-диаграмма и пути
- `docs/tasktracker.md` — пути задач обновлены под `services/spec-converterv2/`
- `docs/changelog.md` — пути обновлены

---

## [2026-02-18] — Принятие архитектурных решений (12 вопросов закрыты)

### Наблюдения

- Все 12 ключевых архитектурных вопросов из `qa.md` получили ответы.
- Решения формируют цельную картину: от UI до деплоя.
- Выбранный стек (Vanilla JS + Custom Elements + Shadow DOM) минимизирует зависимости и обеспечивает изоляцию сервисов.
- Dual mode (standalone + embedded) позволяет развивать сервисы независимо от оболочки.
- Определены 3 будущих сервиса и 3 категории сайдбара.

### Решения

| # | Вопрос | Решение |
|---|--------|---------|
| 1 | UI-фреймворк | Vanilla JS + Web Components (Custom Elements, Shadow DOM) |
| 2 | Standalone/Embedded | Dual mode — Web Component для оболочки, `index.html` для автономной работы |
| 3 | Drag-and-drop | Комбинация: Quick (drop на карточку) + Advanced (модалка/side-panel) |
| 4 | Маршрутизация | Path-based через Nginx (`/api/{service}/`) |
| 5 | Будущие сервисы | OCR, DOCX Merger, Project Validator; категории: Конвертеры, Проверка, Генераторы |
| 6 | Аутентификация | Zero-auth; Basic Auth через Nginx при необходимости |
| 7 | История | Stateless + localStorage (последние 10 операций) |
| 8 | Развёртывание | Docker Compose |
| 9 | API-ключи | `.env` на уровне сервисов + `.env.example` в репо |
| 10 | Ошибки | Badges (👁 vision, красная подсветка), кнопка «Только Vision» |
| 11 | Масштаб | Flask + Gunicorn (2-4 workers); далее Celery + Redis |
| 12 | Тестирование | Snapshot testing на JSON (не Excel), порог > 95% |

### Проблемы

- Нет открытых проблем на данном этапе. Все блокирующие вопросы закрыты.

---

### Изменено
- `docs/project.md` — версия 1.1: конкретизированы технологии, добавлены роадмап сервисов и стратегия тестирования
- `docs/tasktracker.md` — задачи обновлены с учётом принятых решений (Web Components, Dual mode, Gunicorn, `.env`)
- `docs/qa.md` — все 12 вопросов закрыты с зафиксированными решениями

### Добавлено
- Раздел «Роадмап сервисов» в `project.md` (4 сервиса, 3 категории)
- Раздел «Стратегия тестирования» в `project.md` (snapshot, unit, E2E)
- Задача «Snapshot Testing для pdf_text_extractor» в `tasktracker.md`

---

## [2026-02-18] — Инициализация документации и проектирование архитектуры платформы

### Наблюдения

- Проект содержит один работающий микросервис `spec-converterv2` (PDF → Excel), но не имеет общей оболочки и единого интерфейса.
- `spec-converterv2` полностью самостоятелен: собственный frontend (`index.html`), Flask-бэкенд, два пути извлечения данных (text-first + vision fallback).
- Text-first пайплайн показывает ~90.6% совпадений с эталоном. Основные расхождения — порядок строк и мелкое форматирование.
- В проекте отсутствует контейнеризация, CI/CD, централизованное логирование.
- `config.py` содержит API-ключи и присутствует в репозитории (потенциальная проблема безопасности — нужно убедиться, что файл в `.gitignore`).
- Документация разрозненна: множество отдельных `.md` файлов в корне `services/spec-converterv2/` (README, QUICKSTART, OPENROUTER_GUIDE, WSL_DNS_FIX и т.д.).

### Решения

- **Архитектура платформы**: выбрана микросервисная архитектура с единой оболочкой (Shell App) и API Gateway (Nginx).
- **Манифест сервиса**: определён JSON-формат для регистрации сервисов в оболочке (`id`, `name`, `description`, `category`, `endpoints`, `accepts`, `outputType`).
- **Сетка интерфейса**: CSS Grid 3×N, карточки с drag-and-drop, сайдбар с категориями.
- **Стандарты**: обязательный `/health` endpoint, единый формат ошибок, манифест для каждого сервиса.
- **Документация**: создана структурированная папка `/docs/` с четырьмя документами (project, tasktracker, changelog, qa).

### Проблемы

- **Выбор UI-фреймворка**: не определён окончательно (Vanilla JS vs Lit vs Vue 3). Зависит от планов по масштабированию фронтенда и компетенций команды.
- **Совместимость standalone/embedded**: нужно решить, сохранять ли `services/spec-converterv2/frontend/index.html` для автономного использования или перенести весь UI в оболочку.
- **Безопасность секретов**: `config.py` с API-ключами нужно заменить на `.env` и убедиться, что секреты не попадают в репозиторий.
- **Vision fallback стоимость**: LLM Vision вызовы стоят денег и работают медленно (~30-60 сек/страница). Для production нужна очередь задач.

---

### Добавлено
- Документ `/docs/project.md` — полное описание архитектуры платформы
- Документ `/docs/tasktracker.md` — трекер задач по фазам разработки
- Документ `/docs/changelog.md` — дневник наблюдений
- Документ `/docs/qa.md` — архитектурные вопросы

### Изменено
- Нет (первая запись)

### Исправлено
- Нет (первая запись)

---

*Формат записи: каждое значимое изменение документируется с датой, наблюдениями, решениями и проблемами.*
