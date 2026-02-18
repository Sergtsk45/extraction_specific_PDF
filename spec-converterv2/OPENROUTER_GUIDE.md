# 🚀 Запуск с OpenRouter

## Почему OpenRouter?

✅ **Не нужна кредитная карта** - можно пополнить криптой  
✅ **Те же цены** что и у Anthropic ($3/$15 за 1M токенов)  
✅ **Больше моделей** - Claude, GPT-4, Gemini, Llama, и др.  
✅ **Простая интеграция** - OpenAI-совместимый API  
✅ **Единый баланс** - для всех моделей  

## Быстрый старт

### Шаг 1: Получите API ключ OpenRouter

1. Откройте https://openrouter.ai/
2. Зарегистрируйтесь (можно через Google)
3. Перейдите в "Keys" → "Create Key"
4. Скопируйте ключ (начинается с `sk-or-v1-...`)

### Шаг 2: Пополните баланс

**Способы пополнения:**
- 💳 Кредитная карта
- ₿ Криптовалюта (BTC, ETH, USDT и др.)
- 💵 PayPal

**Минимум:** $5  
**Рекомендуется:** $10-20 (хватит на 50-100 спецификаций)

### Шаг 3: Настройте проект

```bash
cd backend

# Переименуйте файлы для OpenRouter
mv app.py app_anthropic.py           # Сохраняем старую версию
mv app_openrouter.py app.py          # Активируем OpenRouter версию

mv requirements.txt requirements_anthropic.txt
mv requirements_openrouter.txt requirements.txt

# Создайте конфиг
cp config_openrouter.py.example config.py

# Отредактируйте config.py
nano config.py
```

В `config.py`:
```python
OPENROUTER_API_KEY = 'sk-or-v1-ваш-ключ-здесь'
MODEL_NAME = 'anthropic/claude-sonnet-4'
```

### Шаг 4: Установите зависимости

```bash
pip install -r requirements.txt
```

### Шаг 5: Запустите

```bash
python app.py
```

## Выбор модели

В `config.py` можно выбрать модель:

### Рекомендуется (лучшее качество):
```python
MODEL_NAME = 'anthropic/claude-sonnet-4'
```
- **Цена:** $3/$15 за 1M токенов
- **Качество:** ⭐⭐⭐⭐⭐
- **Лучше всего работает** с кириллицей и сложными таблицами

### Альтернативы:

```python
# Claude 3.5 Sonnet (чуть старше)
MODEL_NAME = 'anthropic/claude-3.5-sonnet'
# Цена: $3/$15 за 1M токенов

# GPT-4 Vision
MODEL_NAME = 'openai/gpt-4-vision-preview'
# Цена: $5/$15 за 1M токенов
# Немного хуже с кириллицей

# Google Gemini Pro Vision
MODEL_NAME = 'google/gemini-pro-vision'
# Цена: $0.25/$0.50 за 1M токенов
# Дешевле, но может быть хуже качество
```

## Проверка работы

После запуска откройте:
```
http://localhost:5000/health
```

Вы должны увидеть:
```json
{
  "status": "ok",
  "api_key_configured": true,
  "model": "anthropic/claude-sonnet-4"
}
```

## Мониторинг использования

На https://openrouter.ai/activity вы можете:
- Посмотреть историю запросов
- Отслеживать расходы
- Видеть, какие модели использовались

## Сравнение цен

| Модель | Цена (input/output) | Страница PDF | Спецификация 10 стр |
|--------|---------------------|--------------|---------------------|
| Claude Sonnet 4 | $3/$15 | ~2₽ | ~20₽ |
| Claude 3.5 Sonnet | $3/$15 | ~2₽ | ~20₽ |
| GPT-4 Vision | $5/$15 | ~3₽ | ~30₽ |
| Gemini Pro Vision | $0.25/$0.50 | ~0.2₽ | ~2₽ |

**Примечание:** Gemini дешевле, но может хуже работать с кириллицей и сложными таблицами.

## Переключение обратно на Anthropic API

Если захотите вернуться на прямой Anthropic API:

```bash
cd backend
mv app.py app_openrouter.py
mv app_anthropic.py app.py

mv requirements.txt requirements_openrouter.txt
mv requirements_anthropic.txt requirements.txt

pip install -r requirements.txt
```

## Преимущества OpenRouter

1. **Гибкость** - можно легко переключать модели
2. **Доступность** - не нужна кредитная карта
3. **Прозрачность** - видно все расходы
4. **Fallback** - если одна модель недоступна, можно использовать другую
5. **Эксперименты** - легко сравнить качество разных моделей

## Устранение неполадок

### "API key invalid"
- Проверьте, что ключ начинается с `sk-or-v1-`
- Убедитесь, что скопировали ключ полностью

### "Insufficient credits"
- Пополните баланс на https://openrouter.ai/credits

### "Model not found"
- Проверьте список доступных моделей: https://openrouter.ai/models
- Убедитесь, что название модели указано правильно

### Медленная работа
- OpenRouter добавляет ~100-200мс задержки
- Это нормально для агрегатора

---

Готово! Теперь у вас работает версия с OpenRouter 🎉
