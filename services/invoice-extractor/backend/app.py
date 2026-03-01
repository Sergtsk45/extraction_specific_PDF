"""
@file: app.py
@description: Flask REST API для извлечения данных из счетов-фактур (invoice) с использованием LLM
@dependencies: app.extractor, app.excel_builder, app.validators
@created: 2026-03-01
"""
import os
import uuid
import logging
from pathlib import Path
from urllib.parse import quote

from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()

from app.extractor import extract_invoice
from app.excel_builder import build_excel
from app.validators import validate_invoice_data

# ── Логирование ────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ── Безопасность: Валидация путей ──────────────────────────────
def validate_folder_path(path: str, name: str) -> Path:
    """
    Валидирует путь к папке для защиты от Path Injection.
    
    Args:
        path: Путь из конфигурации
        name: Имя параметра для логирования
        
    Returns:
        Path: Валидированный абсолютный путь
        
    Raises:
        ValueError: Если путь выходит за пределы project directory
    """
    project_root = Path(__file__).parent.parent.resolve()
    folder_path = Path(path).resolve()
    
    # Проверяем что путь внутри project directory
    try:
        folder_path.relative_to(project_root)
    except ValueError:
        raise ValueError(
            f"Security: {name} путь '{path}' выходит за пределы проекта. "
            f"Допустимы только пути внутри {project_root}"
        )
    
    return folder_path


# ── Конфигурация ───────────────────────────────────────────────
try:
    UPLOAD_FOLDER = validate_folder_path(
        os.getenv("UPLOAD_FOLDER", "uploads"),
        "UPLOAD_FOLDER"
    )
    OUTPUT_FOLDER = validate_folder_path(
        os.getenv("OUTPUT_FOLDER", "outputs"),
        "OUTPUT_FOLDER"
    )
except ValueError as e:
    logger.error(f"Configuration error: {e}")
    raise

MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", 50))
MAX_CONTENT_LENGTH = MAX_FILE_SIZE_MB * 1024 * 1024
PORT = int(os.getenv("PORT", 5002))

UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)
OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)

# ── Flask app ──────────────────────────────────────────────────
app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH

# CORS: ограничиваем allowed origins
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:8080").split(",")
ALLOWED_ORIGINS = [origin.strip() for origin in ALLOWED_ORIGINS]
CORS(app, origins=ALLOWED_ORIGINS)


# ── Routes ─────────────────────────────────────────────────────

@app.get("/health")
def health():
    """Health check endpoint."""
    logger.info("Health check requested")
    return jsonify({"status": "ok", "version": "1.0.0", "service": "invoice-extractor"})


@app.post("/convert")
def convert():
    """
    Извлечение данных из PDF-счёта и конвертация в JSON/XLSX.
    
    multipart/form-data:
      file         — PDF-файл (обязательно)
      vision_only  — 'true' | 'false' (по умолчанию false)
      provider     — 'anthropic' | 'openrouter' | 'openai'
      output       — 'json' | 'xlsx' | 'both' (по умолчанию 'xlsx')
    """
    logger.info("Convert request received")
    
    # ── Валидация входа ────────────────────────────────────────
    if "file" not in request.files:
        logger.warning("Request missing 'file' field")
        return jsonify({"error": "Поле 'file' обязательно"}), 400

    file = request.files["file"]
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        logger.warning(f"Invalid file type: {file.filename}")
        return jsonify({"error": "Принимаются только PDF-файлы"}), 400

    vision_only = request.form.get("vision_only", "false").lower() == "true"
    provider = request.form.get("provider", os.getenv("LLM_PROVIDER", "anthropic"))
    output_mode = request.form.get("output", "xlsx")  # xlsx | json | both

    logger.info(f"Processing file: {file.filename}, provider: {provider}, output: {output_mode}")

    # ── Сохраняем загруженный файл ─────────────────────────────
    job_id = str(uuid.uuid4())
    pdf_path = UPLOAD_FOLDER / f"{job_id}.pdf"
    file.save(pdf_path)
    logger.info(f"File saved with job_id: {job_id}")

    try:
        # ── Извлечение данных ──────────────────────────────────
        logger.info(f"Extracting invoice data from {pdf_path}")
        invoice_data, used_vision = extract_invoice(
            pdf_path=str(pdf_path),
            vision_only=vision_only,
            provider=provider,
        )

        # ── Валидация ──────────────────────────────────────────
        warnings = validate_invoice_data(invoice_data)
        invoice_data["warnings"] = invoice_data.get("warnings", []) + warnings
        parse_quality = "ok" if not warnings else "partial"
        
        logger.info(f"Extraction complete. Quality: {parse_quality}, Vision used: {used_vision}")

        # ── Формирование ответа ────────────────────────────────
        # URL-encode кириллицы в заголовках для избежания HTTP 502
        invoice_number = invoice_data.get("invoice_number", job_id)
        headers = {
            "X-Vision-Fallback": str(used_vision).lower(),
            "X-Document-Type": "invoice",
            "X-Parse-Quality": parse_quality,
            "X-Job-Id": job_id,
            "X-Invoice-Number": quote(str(invoice_number), safe=''),
        }

        if output_mode == "json":
            logger.info("Returning JSON response")
            return jsonify(invoice_data), 200, headers

        # Строим Excel
        xlsx_path = OUTPUT_FOLDER / f"{job_id}.xlsx"
        logger.info(f"Building Excel file: {xlsx_path}")
        build_excel(invoice_data, str(xlsx_path))

        if output_mode == "xlsx":
            logger.info("Returning XLSX file")
            # URL-encode имени файла для скачивания
            safe_filename = quote(f"invoice_{invoice_number}.xlsx", safe='')
            return send_file(
                str(xlsx_path),
                mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                as_attachment=True,
                download_name=safe_filename,
            ), 200, headers

        # both — возвращаем JSON + путь к файлу
        logger.info("Returning JSON with XLSX reference")
        invoice_data["xlsx_job_id"] = job_id
        return jsonify(invoice_data), 200, headers

    except Exception as exc:
        logger.error(f"Error processing invoice: {exc}", exc_info=True)
        
        # Безопасность: не раскрываем детали ошибок в production
        if app.debug:
            error_message = str(exc)
        else:
            error_message = "Ошибка обработки файла. Обратитесь к администратору."
        
        return jsonify({"error": error_message, "job_id": job_id}), 500

    finally:
        # Удаляем временный PDF
        try:
            pdf_path.unlink(missing_ok=True)
            logger.debug(f"Temporary PDF deleted: {pdf_path}")
        except Exception as e:
            logger.warning(f"Failed to delete temporary PDF: {e}")


# ── Запуск сервера ─────────────────────────────────────────────
if __name__ == "__main__":
    host = os.getenv("FLASK_HOST", "0.0.0.0")
    debug = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    
    logger.info(f"Starting Invoice Extractor service on {host}:{PORT}")
    logger.info(f"Debug mode: {debug}")
    logger.info(f"Upload folder: {UPLOAD_FOLDER.absolute()}")
    logger.info(f"Output folder: {OUTPUT_FOLDER.absolute()}")
    
    app.run(host=host, port=PORT, debug=debug)
