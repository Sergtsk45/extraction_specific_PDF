FROM python:3.11-slim

WORKDIR /app

# Установка системных зависимостей для PDF обработки (pdfplumber, PyMuPDF)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Копирование requirements и установка зависимостей
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копирование кода приложения
COPY backend/ backend/

# Создание директорий для временных файлов
RUN mkdir -p backend/uploads backend/outputs

# Порт Flask API
EXPOSE 5002

# Запуск через gunicorn
CMD ["gunicorn", "-c", "backend/gunicorn.conf.py", "backend.app:app"]
