# 📊 Конвертер спецификаций PDF → Excel

Веб-приложение для автоматической конвертации PDF спецификаций в Excel с помощью AI.

## 🎯 Две версии на выбор

| Провайдер | Регистрация | Цена | Качество | Рекомендация |
|-----------|-------------|------|----------|--------------|
| **Anthropic** | Кредитка | $3/$15 | ⭐⭐⭐⭐⭐ | Для тех, у кого есть карта |
| **OpenRouter** ⭐ | Крипта/Карта | $3/$15 | ⭐⭐⭐⭐⭐ | **Рекомендуется** |

### 🌟 Рекомендуем OpenRouter:

✅ Не нужна кредитная карта - можно пополнить криптой  
✅ Те же цены что и у Anthropic  
✅ Доступ ко всем моделям - Claude, GPT-4, Gemini  
✅ Легко переключаться между моделями  

## 🚀 Быстрый старт с OpenRouter

```bash
# 1. Получите ключ: https://openrouter.ai/
# 2. Переключитесь на OpenRouter
./switch_provider.sh  # выберите 2
# 3. Настройте config.py
cd backend && cp config_openrouter.py.example config.py
# 4. Запустите
pip install -r requirements.txt && python app.py
```

Подробнее: [OPENROUTER_GUIDE.md](OPENROUTER_GUIDE.md)

## Переключение между API

Легко переключайтесь: `./switch_provider.sh` или `switch_provider.bat`

Полная документация: [QUICKSTART.md](QUICKSTART.md)

## Ошибка «Failed to resolve openrouter.ai» в WSL

Если видите ошибку сети с текстом про *NameResolutionError* или *Failed to resolve 'openrouter.ai'* — в WSL не работает DNS. Решение: [WSL_DNS_FIX.md](WSL_DNS_FIX.md)
