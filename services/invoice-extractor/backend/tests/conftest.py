import sys
import os
import io
import importlib.util
from pathlib import Path

import pytest

_BACKEND = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)

_SHARED = os.path.abspath(os.path.join(_BACKEND, '..', '..', '..', 'shared', 'llm_client'))
if os.path.isdir(_SHARED) and _SHARED not in sys.path:
    sys.path.insert(0, _SHARED)

os.environ.setdefault('ANTHROPIC_API_KEY', '')
# Абсолютные пути — validate_folder_path проверяет что путь внутри проекта
os.environ.setdefault('UPLOAD_FOLDER', str(Path(_BACKEND) / 'uploads'))
os.environ.setdefault('OUTPUT_FOLDER', str(Path(_BACKEND) / 'outputs'))

# Обходим конфликт имён app.py vs app/ пакет — используем importlib
_spec = importlib.util.spec_from_file_location("_invoice_main", Path(_BACKEND) / "app.py")
_mod = importlib.util.module_from_spec(_spec)
sys.modules["_invoice_main"] = _mod  # регистрируем для monkeypatch по имени
_spec.loader.exec_module(_mod)
flask_app = _mod.app


@pytest.fixture(scope="session")
def invoice_app_module():
    """Модуль app.py для патчинга через monkeypatch.setattr(invoice_app_module, ...)."""
    return _mod


@pytest.fixture
def client():
    flask_app.config['TESTING'] = True
    with flask_app.test_client() as c:
        yield c


@pytest.fixture
def minimal_pdf_bytes():
    return b"%PDF-1.4\n1 0 obj<</Type /Catalog>>endobj\n%%EOF\n"
