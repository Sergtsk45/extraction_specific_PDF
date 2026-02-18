@echo off
echo ========================================
echo   Конвертер спецификаций PDF - Excel
echo ========================================
echo.

cd backend

echo Проверка виртуального окружения...
if not exist venv (
    echo Создание виртуального окружения...
    python -m venv venv
)

echo Активация окружения...
call venv\Scripts\activate.bat

echo Проверка зависимостей...
pip install -q -r requirements.txt

echo.
echo Запуск сервера...
echo.
python app.py

pause
