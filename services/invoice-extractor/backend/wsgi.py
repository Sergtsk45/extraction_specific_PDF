"""
@file: wsgi.py
@description: WSGI точка входа для Gunicorn.
  Загружает Flask-приложение из app.py в обход конфликта имён с пакетом app/.
@dependencies: app.py
@created: 2026-03-01
"""
import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "_invoice_main",
    Path(__file__).parent / "app.py"
)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

app = _mod.app
