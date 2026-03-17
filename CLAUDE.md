# extraction_specific_PDF

## Проект
Система извлечения данных из PDF-документов с использованием LLM (Anthropic Claude, OpenAI, OpenRouter).
Набор микросервисов на Flask: извлечение инвойсов, конвертация спецификаций, OCR, объединение DOCX.

Стек: Python 3.10+, Flask, Gunicorn, pdfplumber, PyMuPDF, anthropic, openai, openpyxl

## Команды

### invoice-extractor
- Запуск (dev): `cd services/invoice-extractor/backend && flask run --port 5000`
- Запуск (prod): `cd services/invoice-extractor/backend && gunicorn -c gunicorn.conf.py wsgi:app`
- Тесты (все): `pytest services/invoice-extractor/`
- Тесты (один файл): `pytest services/invoice-extractor/backend/tests/test_extractor.py`
- Lint: `ruff check services/`
- Lint fix: `ruff check --fix services/`
- Format: `ruff format services/`
- Type check: `mypy services/invoice-extractor/backend/app/`
- Зависимости: `pip install -r services/invoice-extractor/backend/requirements.txt`

### spec-converterv2
- Запуск (dev): `cd services/spec-converterv2/backend && flask run --port 5001`
- Тесты: `pytest services/spec-converterv2/`
- Lint: `ruff check services/spec-converterv2/`

### Все сервисы
- Lint всего: `ruff check services/`
- Тесты всего: `pytest services/`

## Структура проекта
```
services/
├── invoice-extractor/backend/
│   ├── app.py              # Flask entry point
│   ├── app/
│   │   ├── extractor.py    # PDF extraction (pdfplumber + PyMuPDF)
│   │   ├── llm_client.py   # Anthropic/OpenAI/OpenRouter abstraction
│   │   ├── normalizer.py   # Нормализация извлечённых данных
│   │   ├── validators.py   # Валидация данных
│   │   └── excel_builder.py # Генерация Excel (openpyxl)
│   ├── wsgi.py
│   └── requirements.txt
├── spec-converterv2/backend/
│   ├── app.py
│   ├── pdf_text_extractor.py
│   └── spec_utils.py
├── docx-merger/
├── ocr/
└── project-validator/
docs/           # Документация (changelog, tasktracker, dev guide)
ai_docs/        # AI-generated отчёты и планы
```

## Стандарты кода
- Именование: snake_case для функций/переменных, PascalCase для классов
- Импорты: stdlib → third-party → local, каждая группа через пустую строку
- Обработка ошибок: возвращать `{"error": "...", "details": "..."}` с HTTP-кодом; логировать через `logging`
- Секреты: только через `.env` + `python-dotenv`, никогда не хардкодить
- Максимальная длина функции: 50 строк, метода: 30 строк
- Не оставляй `print()` для отладки — используй `logging`
- Используй ранний return вместо глубокой вложенности
- LLM-клиент абстрагирован в `llm_client.py` — не вызывай API напрямую из других модулей

## Тестирование
- Фреймворк: pytest
- Паттерн именования: `test_*.py`
- Расположение: `services/<service>/backend/tests/`
- Фикстуры: pytest fixtures в `conftest.py`
- Моки: `pytest-mock` / `unittest.mock` для LLM-клиентов, файловой системы, внешних API
- Не мокай внутреннюю логику — только внешние зависимости (Anthropic API, OpenAI API, файловая система)
- Покрытие: тесты на все публичные функции + edge cases (пустой PDF, невалидный формат, ошибки LLM)
- Один assert на логическую проверку, понятные имена: `test_extract_returns_empty_dict_for_blank_pdf`

## Git
- Формат коммитов: conventional commits (`feat:`, `fix:`, `refactor:`, `test:`, `docs:`, `chore:`)
- Ветки: `feature/*`, `fix/*`, `refactor/*`
- Перед коммитом: `ruff check` + `mypy` + `pytest` должны проходить

## Документация
- Основная: `docs/` (changelog.md, tasktracker.md, microservice-development-guide.md)
- AI-отчёты: `ai_docs/`
- Обновлять `docs/changelog.md` при изменении публичного API сервисов
- Docstring для публичных функций (стиль Google docstring)
- При добавлении нового сервиса — обновить `docs/microservice-development-guide.md`
