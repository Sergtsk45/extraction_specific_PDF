@echo off
echo =========================================
echo   Выбор API провайдера
echo =========================================
echo.
echo Выберите провайдер:
echo 1) Anthropic API (прямой доступ к Claude)
echo 2) OpenRouter (агрегатор моделей)
echo.
set /p choice="Ваш выбор (1 или 2): "

cd backend

if "%choice%"=="1" (
    echo.
    echo Переключение на Anthropic API...
    
    if exist app.py move /y app.py app_current.py >nul
    
    if exist app_anthropic.py (
        copy /y app_anthropic.py app.py >nul
    ) else (
        if exist app_current.py move /y app_current.py app.py >nul
    )
    
    if exist requirements_anthropic.txt copy /y requirements_anthropic.txt requirements.txt >nul
    
    echo OK Переключено на Anthropic API
    echo.
    echo Настройте config.py:
    echo   ANTHROPIC_API_KEY = 'sk-ant-...'
    echo.
    echo Установите зависимости:
    echo   pip install -r requirements.txt
    
) else if "%choice%"=="2" (
    echo.
    echo Переключение на OpenRouter...
    
    if exist app.py move /y app.py app_current.py >nul
    
    if exist app_openrouter.py (
        copy /y app_openrouter.py app.py >nul
    ) else (
        if exist app_current.py move /y app_current.py app.py >nul
    )
    
    if exist requirements_openrouter.txt copy /y requirements_openrouter.txt requirements.txt >nul
    
    echo OK Переключено на OpenRouter
    echo.
    echo Настройте config.py:
    echo   OPENROUTER_API_KEY = 'sk-or-v1-...'
    echo   MODEL_NAME = 'anthropic/claude-sonnet-4'
    echo.
    echo Установите зависимости:
    echo   pip install -r requirements.txt
    echo.
    echo Подробнее: ..\OPENROUTER_GUIDE.md
) else (
    echo Неверный выбор!
    pause
    exit /b 1
)

echo.
pause
