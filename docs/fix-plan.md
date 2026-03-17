# План исправлений — Extraction Specific PDF

> **Дата:** 2026-03-17  
> **Источник:** Code Review на основе GitHub-репозитория  
> **Статус:** Черновик  
> **Всего задач:** 13 (3 критических, 7 серьёзных, 3 некритичных)

---

## 🔴 Приоритет 1 — Критические (исправить немедленно)

### FIX-001: Утечка секретов и мёртвый код с API-ключами

**Проблема:** В репозитории лежат backup-файлы (`app_anthropic_only.py.backup`, `app_openrouter.py`) с `from config import ANTHROPIC_API_KEY`. Если `config.py` когда-либо попадал в Git-историю — ключи скомпрометированы. Кроме того, это мёртвый код, который путает при навигации по проекту.

**Влияние:** Утечка API-ключей → финансовые потери (чужие вызовы LLM за ваш счёт).

**Подзадачи:**

- [x] **FIX-001.1** — Проверить Git-историю на наличие `config.py` с секретами:
  ```bash
  git log --all --diff-filter=A -- "**/config.py"
  git log --all -p -- "**/config.py" | grep -i "api_key\|secret"
  ```
- [x] **FIX-001.2** — Если найден: ротировать ВСЕ API-ключи. Проверено — реальных ключей в истории нет, только плейсхолдеры. Ротация не требуется.
- [x] **FIX-001.3** — Очистить Git-историю от `config.py`. Проверено — `config.py` в истории отсутствует. Очистка не требуется.
- [x] **FIX-001.4** — Удалить мёртвые файлы из репозитория (`git rm`):
  - `spec-converterv2/backend/app_anthropic_only.py.backup`
  - `spec-converterv2/backend/app_openrouter.py`
  - `spec-converterv2/backend/config.py.example`
  - `spec-converterv2/backend/config_anthropic.example`
  - `spec-converterv2/backend/config_openrouter.example`
  - `spec-converterv2/backend/config_openrouter.py.example`
  - `spec-converterv2/backend/config_universal.py.example`
- [x] **FIX-001.5** — Добавить в `.gitignore`: уже было (`*.backup`, `*.bak`, `config*.py`, `config*.example`)
- [x] **FIX-001.6** — Убедиться, что `.env` файлы обоих сервисов есть в `.gitignore`: уже было (`**/backend/.env`)

**Файлы:** `.gitignore`, `spec-converterv2/backend/app_anthropic_only.py.backup`, `spec-converterv2/backend/app_openrouter.py`  
**Оценка:** 1–2 часа

---

### FIX-002: CORS без ограничений в spec-converterv2

**Проблема:** В `services/spec-converterv2/backend/app.py` стоит `CORS(app)` без указания origins — эквивалент `Access-Control-Allow-Origin: *`. Любой сайт в интернете может отправлять запросы на API конвертера. В `invoice-extractor` это уже исправлено — `CORS(app, origins=ALLOWED_ORIGINS)`.

**Влияние:** Злоумышленник может создать страницу, которая дёргает ваш API и тратит ваши LLM-ключи.

**Подзадачи:**

- [x] **FIX-002.1** — Добавить в `services/spec-converterv2/backend/.env.example`:
  ```
  ALLOWED_ORIGINS=http://localhost:8080,http://localhost:5001
  ```
- [x] **FIX-002.2** — Обновить `services/spec-converterv2/backend/app.py`:
  ```python
  # Было:
  CORS(app)

  # Стало:
  ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:8080").split(",")
  ALLOWED_ORIGINS = [origin.strip() for origin in ALLOWED_ORIGINS]
  CORS(app, origins=ALLOWED_ORIGINS)
  ```
- [ ] **FIX-002.3** — Обновить `.env` на сервере с актуальными origins.

**Файлы:** `services/spec-converterv2/backend/app.py`, `services/spec-converterv2/backend/.env.example`  
**Оценка:** 15 минут

---

### FIX-003: Нет валидации содержимого загружаемых файлов

**Проблема:** Оба сервиса проверяют только расширение файла (`.pdf`). Переименованный `malware.exe` → `malware.pdf` пройдёт проверку и будет сохранён на диск. Нет проверки magic bytes и MIME-типа.

**Влияние:** Загрузка произвольных файлов на сервер; потенциальное исполнение вредоносного кода при дальнейшей обработке.

**Подзадачи:**

- [x] **FIX-003.1** — Добавить `python-magic` в `requirements.txt` обоих сервисов:
  ```
  python-magic>=0.4.27
  ```
- [x] **FIX-003.2** — Создать общую утилиту валидации (или добавить в каждый сервис):
  ```python
  import magic

  def validate_pdf(file_storage):
      """Проверяет, что загруженный файл действительно PDF."""
      # 1. Проверка расширения
      filename = file_storage.filename or ""
      if not filename.lower().endswith(".pdf"):
          return False, "Только PDF файлы"

      # 2. Проверка magic bytes
      header = file_storage.read(8)
      file_storage.seek(0)  # Вернуть указатель
      if not header.startswith(b"%PDF-"):
          return False, "Файл не является настоящим PDF"

      # 3. (Опционально) Проверка MIME через libmagic
      mime = magic.from_buffer(header, mime=True)
      if mime != "application/pdf":
          return False, f"Неверный MIME-тип: {mime}"

      return True, None
  ```
- [x] **FIX-003.3** — Интегрировать валидацию в `convert_pdf()` обоих сервисов (перед `f.save()`).
- [x] **FIX-003.4** — Добавить ограничение размера файла на уровне Flask в spec-converterv2 (в invoice-extractor уже есть `MAX_CONTENT_LENGTH`):
  ```python
  app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024  # 50 MB
  ```

**Файлы:** оба `app.py`, оба `requirements.txt`  
**Оценка:** 1 час

---

## 🟡 Приоритет 2 — Серьёзные (исправить на этой неделе)

### FIX-004: Race condition и потеря кириллицы при сохранении файлов

**Проблема:** `secure_filename("Спецификация ВК2.pdf")` → `"_2.pdf"`. Два одновременных запроса с одинаковым именем файла перезаписывают друг друга. UUID уже импортирован в invoice-extractor, но не используется при сохранении.

**Влияние:** Потеря файлов пользователей при параллельных запросах; невозможность идентифицировать файл по имени.

**Подзадачи:**

- [x] **FIX-004.1** — Создать утилиту генерации безопасного уникального имени:
  ```python
  import uuid
  from werkzeug.utils import secure_filename

  def safe_filename(original: str) -> str:
      """UUID-префикс + безопасное имя. Сохраняет расширение."""
      ext = original.rsplit(".", 1)[-1].lower() if "." in original else ""
      safe = secure_filename(original)
      # Если secure_filename вырезал всё (кириллица) — используем только UUID
      base = safe.rsplit(".", 1)[0] if safe and safe != f".{ext}" else "file"
      return f"{uuid.uuid4().hex[:12]}_{base}.{ext}"
  ```
- [x] **FIX-004.2** — Заменить `secure_filename(f.filename)` на `safe_filename(f.filename)` в обоих сервисах. (invoice-extractor уже использовал UUID; spec-converterv2 обновлён)
- [x] **FIX-004.3** — Сохранить оригинальное имя для `download_name` в ответе (spec-converterv2 обновлён; invoice-extractor использует invoice_number).

**Файлы:** `services/spec-converterv2/backend/app.py`, `services/invoice-extractor/backend/app.py`  
**Оценка:** 30 минут

---

### FIX-005: Отсутствие таймаутов на внешние API-вызовы

**Проблема:** Vision-вызовы к Anthropic/OpenRouter/OpenAI не имеют явных таймаутов на уровне HTTP-клиента. Если API провайдера зависнет — воркер Gunicorn блокируется навсегда (gunicorn timeout убьёт воркер, но это грубый механизм).

**Влияние:** Один зависший запрос к API может заблокировать воркер на неопределённое время.

**Подзадачи:**

- [x] **FIX-005.1** — Добавить `timeout` при создании клиентов в spec-converterv2:
  ```python
  # Anthropic
  client = anthropic.Anthropic(api_key=api_key, timeout=120.0)

  # OpenAI / OpenRouter
  client = openai.OpenAI(api_key=api_key, timeout=120.0)

  # requests (если используется напрямую)
  requests.post(url, timeout=(5, 120))  # (connect, read)
  ```
- [x] **FIX-005.2** — Вынести значение таймаута в `.env`: добавлен `REQUEST_TIMEOUT_SEC=120` в `.env.example` обоих сервисов.
- [x] **FIX-005.3** — Проверить invoice-extractor: уже использовал `TIMEOUT = int(os.getenv("REQUEST_TIMEOUT_SEC", 120))` во всех провайдерах.

**Файлы:** `services/spec-converterv2/backend/app.py`, `services/invoice-extractor/backend/app/llm_client.py`  
**Оценка:** 30 минут

---

### FIX-006: print() вместо logging в spec-converterv2

**Проблема:** Весь `spec-converterv2` использует `print()` для вывода. В продакшене это потеря контроля: нет уровней (INFO/WARNING/ERROR), нет timestamps (Gunicorn добавляет свои, но для `print` — нет), проблемы с буферизацией stdout в Docker.

**Влияние:** Невозможность фильтрации логов, потеря вывода при буферизации.

**Подзадачи:**

- [x] **FIX-006.1** — Добавить настройку logging по аналогии с invoice-extractor:
  ```python
  import logging
  logging.basicConfig(
      level=logging.INFO,
      format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
  )
  logger = logging.getLogger(__name__)
  ```
- [x] **FIX-006.2** — Заменить все `print()` вызовы (28 замен в app.py):
  - `print(f"✅ ...")` → `logger.info(...)`
  - `print(f"⚠️ ...")` → `logger.warning(...)`
  - `print(f"❌ ...")` → `logger.error(...)`
  - Диагностические в `process_pdf()` → `logger.debug(...)`
  - Трейсбек в except → `logger.exception(...)`
- [x] **FIX-006.3** — Добавить `PYTHONUNBUFFERED=1` в `.env.example` (для Docker).

**Файлы:** `services/spec-converterv2/backend/app.py`, `services/spec-converterv2/backend/pdf_text_extractor.py`  
**Оценка:** 1 час

---

### FIX-007: Дублирование LLM-клиента между сервисами

**Проблема:** Обёртки над Anthropic/OpenRouter/OpenAI (создание клиента, отправка изображения, парсинг JSON-ответа) реализованы дважды — в `spec-converterv2/backend/app.py` и `invoice-extractor/backend/app/llm_client.py`. Промпты разные (это нормально), но инфраструктурный код — копипаста.

**Влияние:** При обновлении API провайдера или добавлении нового — правки в двух местах. Баг в одном сервисе не исправляется в другом.

**Подзадачи:**

- [x] **FIX-007.1** — Создать общий пакет `shared/llm_client/`:
  ```
  project-root/
  ├── shared/
  │   └── llm_client/
  │       ├── pyproject.toml
  │       └── llm_client/
  │           ├── __init__.py
  │           ├── client.py    # call_vision_llm(images, prompt, provider, ...)
  │           ├── vision.py    # pdf_to_images, parse_json_response
  │           └── config.py    # get_api_key, DEFAULT_TIMEOUT, DEFAULT_MAX_TOKENS
  ```
- [x] **FIX-007.2** — Вынести общие функции:
  - `call_vision_llm(images, prompt, provider, *, system_prompt, api_key, model, timeout, max_tokens, temperature)` → str
  - `pdf_to_images(pdf_path, zoom=4, max_size_bytes=4MB)` → list[(bytes, media_type)]
  - `parse_json_response(raw_text)` → dict
  - `get_api_key(provider)` → str | None
- [x] **FIX-007.3** — Рефакторинг обоих сервисов: заменить локальные функции на импорт из `shared/`.
  - invoice-extractor: `app/llm_client.py` — тонкая обёртка над shared, сохранён оригинальный API
  - spec-converterv2: убраны `_extract_via_*`, `_extract_from_image`, `_pdf_to_images`, `_parse_json_response` (105 строк дубликатов)
- [x] **FIX-007.4** — Оформлен как installable package (`pip install -e shared/llm_client`); добавлен в `requirements.txt` обоих сервисов.

**Файлы:** новая директория `shared/`, оба `app.py`  
**Оценка:** 3–4 часа  
**Зависимости:** FIX-005 (таймауты)

---

### FIX-008: Создание Nginx Gateway

**Проблема:** Задача "Настройка Nginx" в трекере со статусом "Не начата". Сейчас всё роутится через `dev_server.py` на `urllib`, который не поддерживает streaming, chunked encoding, имеет жёсткий таймаут 60 сек и не обрабатывает ошибки multipart корректно. Нет rate limiting, gzip, кеширования статики.

**Влияние:** Невозможность использования в продакшене; уязвимость к slow loris, flood-атакам; низкая производительность раздачи статики.

**Подзадачи:**

- [x] **FIX-008.1** — Создать `gateway/nginx.conf`:
  ```nginx
  worker_processes auto;
  
  events {
      worker_connections 1024;
  }
  
  http {
      include       mime.types;
      sendfile      on;
      gzip          on;
      gzip_types    text/css application/javascript application/json;
      
      client_max_body_size 50M;
      
      # Rate limiting
      limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
      
      upstream spec-converter {
          server 127.0.0.1:5001;
      }
      
      upstream invoice-extractor {
          server 127.0.0.1:5002;
      }
      
      server {
          listen 8080;
          
          # Shell App (статика)
          location / {
              root /path/to/project-root;
              index shell/index.html;
              try_files $uri $uri/ /shell/index.html;
          }
          
          # spec-converter API
          location /api/spec-converter/ {
              limit_req zone=api burst=20 nodelay;
              proxy_pass http://spec-converter/;
              proxy_read_timeout 180s;  # Vision может быть долгим
              proxy_set_header Host $host;
              proxy_set_header X-Real-IP $remote_addr;
          }
          
          # invoice-extractor API
          location /api/invoice-extractor/ {
              limit_req zone=api burst=20 nodelay;
              proxy_pass http://invoice-extractor/;
              proxy_read_timeout 180s;
              proxy_set_header Host $host;
              proxy_set_header X-Real-IP $remote_addr;
          }
      }
  }
  ```
- [x] **FIX-008.2** — Убрать `flask-cors` из обоих сервисов. Через gateway (Nginx/dev_server.py) фронт и API на одном origin :8080 — CORS не нужен.
- [x] **FIX-008.3** — Создать production systemd-юниты в `gateway/systemd/` (nginx.service, spec-converterv2.service с gunicorn, invoice-extractor.service). Обновлён deployed unit spec-converterv2 (python app.py → gunicorn). Добавлены wsgi.py и gunicorn.conf.py для spec-converterv2.
- [x] **FIX-008.4** — Обновлён `dev_server.py`: добавлено предупреждение "[DEV] только для разработки, для production — gateway/nginx.conf".

**Файлы:** `gateway/nginx.conf`, systemd units  
**Оценка:** 2–3 часа  
**Зависимости:** FIX-002 (CORS)

---

### FIX-009: Отсутствие тестов

**Проблема:** Snapshot testing запланирован, но не реализован. Нет ни одного автоматического теста. Для сервиса с точностью ~90.6% любое изменение может незаметно ухудшить качество парсинга.

**Влияние:** Регрессии при рефакторинге; невозможность уверенно деплоить изменения.

**Подзадачи:**

- [x] **FIX-009.1** — Создать `tests/` в каждом сервисе (conftest, health, convert, validators, text_extractor, normalizer).
- [x] **FIX-009.2** — Unit-тесты без snapshot (чистые функции; snapshot требует эталонного PDF).
- [x] **FIX-009.3** — Добавить `pytest` и `pytest-cov` в `requirements.txt`.
- [x] **FIX-009.4** — Написать тесты для invoice-extractor (62 теста: validators, normalizer, convert API, health).
- [x] **FIX-009.5** — Добавить `Makefile` в корень проекта.

**Итог:** 125 тестов (62 invoice-extractor + 63 spec-converterv2), все проходят.

**Файлы:** `tests/` в обоих сервисах, `requirements.txt`  
**Оценка:** 4–6 часов (базовый набор)  
**Зависимости:** нет

---

### FIX-010: Нет CI/CD

**Проблема:** Нет автоматической проверки при коммите. Нет линтинга, нет запуска тестов в пайплайне. Каждый деплой — ручной.

**Влияние:** Баги попадают в main без проверки; ручной деплой error-prone.

**Подзадачи:**

- [ ] **FIX-010.1** — Создать `.github/workflows/ci.yml`:
  ```yaml
  name: CI
  on: [push, pull_request]
  jobs:
    test:
      runs-on: ubuntu-latest
      steps:
        - uses: actions/checkout@v4
        - uses: actions/setup-python@v5
          with:
            python-version: "3.11"
        - name: Install spec-converterv2 deps
          run: pip install -r services/spec-converterv2/backend/requirements.txt
        - name: Install invoice-extractor deps
          run: pip install -r services/invoice-extractor/backend/requirements.txt
        - name: Install test deps
          run: pip install pytest pytest-cov
        - name: Run tests
          run: pytest --cov
    lint:
      runs-on: ubuntu-latest
      steps:
        - uses: actions/checkout@v4
        - run: pip install ruff
        - run: ruff check .
  ```
- [ ] **FIX-010.2** — Добавить `ruff.toml` для линтинга:
  ```toml
  line-length = 120
  target-version = "py311"
  ```
- [ ] **FIX-010.3** — (Опционально) Добавить шаг деплоя через SSH или Docker push.

**Файлы:** `.github/workflows/ci.yml`, `ruff.toml`  
**Оценка:** 2 часа  
**Зависимости:** FIX-009 (тесты)

---

## 🟢 Приоритет 3 — Некритичные (запланировать)

### FIX-011: Жёстко зашитые порты и конфигурация

**Проблема:** Порты `5001`, `5002`, `8080` захардкожены в `dev_server.py`, `manifest.json`, shell-конфигах. Изменение порта одного сервиса требует правки в 5+ файлах.

**Подзадачи:**

- [ ] **FIX-011.1** — Централизовать порты в корневом `.env`:
  ```
  SHELL_PORT=8080
  SPEC_CONVERTER_PORT=5001
  INVOICE_EXTRACTOR_PORT=5002
  ```
- [ ] **FIX-011.2** — Обновить `dev_server.py` для чтения портов из `.env` (через `python-dotenv`).
- [ ] **FIX-011.3** — Обновить `shell/js/config.js`: сделать base URL настраиваемым или автоопределяемым по `window.location`.

**Оценка:** 1 час

---

### FIX-012: Health endpoint утечка информации

**Проблема:** `/health` в spec-converterv2 возвращает `provider`, `model`, `configured`. Это утечка деталей инфраструктуры.

**Подзадачи:**

- [ ] **FIX-012.1** — Оставить минимальный ответ для внешних потребителей:
  ```json
  {"status": "ok", "service": "spec-converterv2", "version": "2.0.0"}
  ```
- [ ] **FIX-012.2** — Вынести детальную информацию в отдельный endpoint `/health/details` (или отдавать только при локальном запросе).

**Оценка:** 15 минут

---

### FIX-013: Консолидация документации spec-converterv2

**Проблема:** В корне `services/spec-converterv2/` лежат: `README.md`, `QUICKSTART.md`, `OPENROUTER_GUIDE.md`, `WSL_DNS_FIX.md`, `ИСПРАВЛЕНИЕ.md`, `TEXT_FIRST_PIPELINE.md`, `switch_provider.sh`, `start.sh`. Для нового разработчика — хаос.

**Подзадачи:**

- [ ] **FIX-013.1** — Объединить в один `README.md`: быстрый старт, архитектура, API, провайдеры.
- [ ] **FIX-013.2** — `WSL_DNS_FIX.md` → перенести в `docs/troubleshooting.md` (это не специфика сервиса).
- [ ] **FIX-013.3** — `ИСПРАВЛЕНИЕ.md` → архивировать или удалить (исторический документ, исправления уже применены).
- [ ] **FIX-013.4** — `TEXT_FIRST_PIPELINE.md` → оставить как `docs/text-first-pipeline.md` (полезная техническая документация).
- [ ] **FIX-013.5** — `OPENROUTER_GUIDE.md` → секция в README (после FIX-007 провайдеры будут в shared).

**Оценка:** 1–2 часа

---

## Порядок выполнения

```
Неделя 1 (критичные + быстрые)
│
├─ FIX-001  Секреты в Git .................. 1-2ч
├─ FIX-002  CORS spec-converterv2 .......... 15мин
├─ FIX-003  Валидация PDF .................. 1ч
├─ FIX-004  Race condition + кириллица ..... 30мин
├─ FIX-005  Таймауты LLM-клиентов ......... 30мин
├─ FIX-006  Logging вместо print ........... 1ч
└─ FIX-012  Health endpoint ................ 15мин
                                       Итого: ~5ч

Неделя 2 (инфраструктура)
│
├─ FIX-007  Shared LLM-клиент .............. 3-4ч
├─ FIX-008  Nginx Gateway .................. 2-3ч
├─ FIX-009  Тесты (базовый набор) .......... 4-6ч
└─ FIX-011  Централизация конфигурации ..... 1ч
                                       Итого: ~12ч

Неделя 3 (CI/CD + документация)
│
├─ FIX-010  GitHub Actions CI .............. 2ч
└─ FIX-013  Документация spec-converterv2 .. 1-2ч
                                       Итого: ~4ч
```

**Общая оценка: ~21 час работы (3 рабочих дня).**

---

## Дополнительно: что НЕ вошло в план (запланировано в фазах 2–4)

Следующие пункты уже есть в `tasktracker.md` и не дублируются здесь:

- Контейнеризация (Dockerfile + Docker Compose)
- Task Queue (Celery + Redis) для асинхронной обработки
- Централизованное логирование (ELK / Loki)
- Нагрузочное тестирование
- Точность парсинга: 59% на листе 2 (требует исследования — порядок строк)
