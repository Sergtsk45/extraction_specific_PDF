#!/bin/bash

echo "========================================"
echo "  Конвертер спецификаций PDF → Excel"
echo "========================================"
echo ""

cd backend

echo "Проверка виртуального окружения..."
if [ ! -d "venv" ]; then
    echo "Создание виртуального окружения..."
    python3 -m venv venv
fi

echo "Проверка зависимостей..."
venv/bin/pip install -q -r requirements.txt

echo ""
echo "Запуск сервера (через venv)..."
echo ""
venv/bin/python app.py
