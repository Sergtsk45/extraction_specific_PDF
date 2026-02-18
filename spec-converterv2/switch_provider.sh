#!/bin/bash

echo "========================================="
echo "  Выбор API провайдера"
echo "========================================="
echo ""
echo "Выберите провайдер:"
echo "1) Anthropic API (прямой доступ к Claude)"
echo "2) OpenRouter (агрегатор моделей)"
echo ""
read -p "Ваш выбор (1 или 2): " choice

cd backend

if [ "$choice" == "1" ]; then
    echo ""
    echo "Переключение на Anthropic API..."
    
    # Сохраняем текущую версию
    [ -f app.py ] && mv app.py app_current.py
    
    # Активируем Anthropic версию
    if [ -f app_anthropic.py ]; then
        cp app_anthropic.py app.py
    else
        [ -f app_current.py ] && mv app_current.py app.py
    fi
    
    # Переключаем requirements
    [ -f requirements_anthropic.txt ] && cp requirements_anthropic.txt requirements.txt
    
    echo "✅ Переключено на Anthropic API"
    echo ""
    echo "Настройте config.py:"
    echo "  ANTHROPIC_API_KEY = 'sk-ant-...'"
    echo ""
    echo "Установите зависимости:"
    echo "  pip install -r requirements.txt"
    
elif [ "$choice" == "2" ]; then
    echo ""
    echo "Переключение на OpenRouter..."
    
    # Сохраняем текущую версию
    [ -f app.py ] && mv app.py app_current.py
    
    # Активируем OpenRouter версию
    if [ -f app_openrouter.py ]; then
        cp app_openrouter.py app.py
    else
        [ -f app_current.py ] && mv app_current.py app.py
    fi
    
    # Переключаем requirements
    [ -f requirements_openrouter.txt ] && cp requirements_openrouter.txt requirements.txt
    
    echo "✅ Переключено на OpenRouter"
    echo ""
    echo "Настройте config.py:"
    echo "  OPENROUTER_API_KEY = 'sk-or-v1-...'"
    echo "  MODEL_NAME = 'anthropic/claude-sonnet-4'"
    echo ""
    echo "Установите зависимости:"
    echo "  pip install -r requirements.txt"
    echo ""
    echo "Подробнее: ../OPENROUTER_GUIDE.md"
else
    echo "Неверный выбор!"
    exit 1
fi
