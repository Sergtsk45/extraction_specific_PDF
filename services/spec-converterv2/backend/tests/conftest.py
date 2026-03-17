import sys
import os
import io

import pytest

_BACKEND = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)

_SHARED = os.path.abspath(os.path.join(_BACKEND, '..', '..', '..', 'shared', 'llm_client'))
if os.path.isdir(_SHARED) and _SHARED not in sys.path:
    sys.path.insert(0, _SHARED)

os.environ.setdefault('API_PROVIDER', '')
os.environ.setdefault('MODEL_NAME', '')
os.environ.setdefault('OPENROUTER_API_KEY', '')

from app import app as flask_app


@pytest.fixture
def client():
    flask_app.config['TESTING'] = True
    with flask_app.test_client() as c:
        yield c


@pytest.fixture
def minimal_pdf_bytes():
    return b"%PDF-1.4\n1 0 obj<</Type /Catalog>>endobj\n%%EOF\n"


@pytest.fixture
def not_pdf_bytes():
    return b"PK\x03\x04fake zip content here"
