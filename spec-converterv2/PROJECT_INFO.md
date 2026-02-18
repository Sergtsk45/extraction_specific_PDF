# 📊 Конвертер спецификаций PDF → Excel

## О проекте

Простое веб-приложение для автоматической конвертации PDF спецификаций в Excel с использованием Claude AI.

### Что делает:
✅ Распознаёт таблицы в PDF спецификациях  
✅ Извлекает данные через Claude AI  
✅ Создаёт отформатированный Excel файл  
✅ Сохраняет структуру: объединённые ячейки, иерархию, спецсимволы  

### Технологии:
- **Frontend**: HTML5, CSS3, JavaScript (Drag & Drop API)
- **Backend**: Python, Flask, PyMuPDF
- **AI**: Claude Sonnet 4 (Anthropic API)
- **Output**: OpenPyXL для создания Excel

### Точность:
- 85-92% автоматического распознавания
- Рекомендуется быстрая проверка результата

### Стоимость:
- ~2₽ за страницу PDF
- ~20₽ за типичную спецификацию (10 страниц)

### Скорость:
- 1-2 минуты на обработку 10-страничного PDF

## Файлы проекта

```
spec-converter/
│
├── frontend/
│   └── index.html          # Веб-интерфейс с drag-and-drop
│
├── backend/
│   ├── app.py             # Flask сервер
│   ├── spec_utils.py      # Библиотека создания Excel
│   ├── config.py.example  # Шаблон конфига
│   └── requirements.txt   # Python зависимости
│
├── start.bat              # Быстрый запуск (Windows)
├── start.sh               # Быстрый запуск (Linux/Mac)
├── QUICKSTART.md          # Инструкция за 3 минуты
└── README.md              # Полная документация
```

## Быстрый старт

1. **Получите API ключ**: https://console.anthropic.com/
2. **Создайте config.py**: `cp backend/config.py.example backend/config.py`
3. **Вставьте ключ** в config.py
4. **Запустите**: `./start.sh` или `start.bat`
5. **Откройте** frontend/index.html в браузере
6. **Перетащите** PDF и нажмите кнопку

Подробнее: [QUICKSTART.md](QUICKSTART.md)

## Требования

### Системные:
- Python 3.8+
- 200 МБ свободного места
- Современный браузер (Chrome, Firefox, Safari, Edge)

### API:
- API ключ Claude (получить на console.anthropic.com)
- Баланс на аккаунте Anthropic

## Безопасность

✅ Файлы обрабатываются локально  
✅ PDF отправляются только в Claude API  
✅ Временные файлы удаляются автоматически  
⚠️  НЕ коммитьте config.py с реальным ключом!  

## Поддержка

Проблемы? Смотрите раздел "Устранение неполадок" в [README.md](README.md)

---

Создано для упрощения работы со спецификациями ❤️
