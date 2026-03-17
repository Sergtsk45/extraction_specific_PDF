"""Tests for POST /convert endpoint of invoice-extractor."""

import io

MINIMAL_PDF = b"%PDF-1.4\n1 0 obj<</Type /Catalog>>endobj\n%%EOF\n"
NOT_PDF = b"PK\x03\x04fake zip content here"

SAMPLE_INVOICE = {
    "document_type": "supplier_invoice",
    "invoice_number": "123",
    "invoice_date": "2026-01-15",
    "supplier": {
        "name": "ООО Поставщик",
        "inn": "1234567890",
        "kpp": "123456789",
        "address": "г. Москва",
        "bank": {
            "name": "Банк",
            "bik": "044525001",
            "account": "40702810000000000001",
            "corr_account": "30101810000000000001",
        },
    },
    "buyer": {
        "name": "ООО Покупатель",
        "inn": "0987654321",
        "kpp": "987654321",
        "address": "г. СПб",
    },
    "items": [
        {
            "line_no": 1,
            "article": "A001",
            "name": "Товар 1",
            "unit": "шт",
            "qty": 10.0,
            "price": 100.0,
            "amount_wo_vat": 1000.0,
            "discount": "",
            "vat_rate": "20",
            "vat_amount": 200.0,
            "amount_w_vat": 1200.0,
        }
    ],
    "totals": {"total_wo_vat": 1000.0, "vat_total": 200.0, "total_w_vat": 1200.0},
    "pages": 1,
    "warnings": [],
}


def _upload_pdf(client, content: bytes, filename: str = 'invoice.pdf', extra: dict = None):
    data = {'file': (io.BytesIO(content), filename)}
    if extra:
        data.update(extra)
    return client.post('/convert', data=data, content_type='multipart/form-data')


# ── Validation errors ──────────────────────────────────────────────────────────

def test_convert_returns_400_when_no_file(client):
    response = client.post('/convert', data={}, content_type='multipart/form-data')
    assert response.status_code == 400


def test_convert_no_file_error_message_present(client):
    data = client.post('/convert', data={}, content_type='multipart/form-data').get_json()
    assert 'error' in data


def test_convert_returns_400_for_wrong_extension(client):
    response = _upload_pdf(client, MINIMAL_PDF, filename='invoice.docx')
    assert response.status_code == 400


def test_convert_wrong_extension_error_mentions_pdf(client):
    data = _upload_pdf(client, MINIMAL_PDF, filename='invoice.docx').get_json()
    assert 'error' in data


def test_convert_returns_400_for_wrong_magic_bytes(client):
    response = _upload_pdf(client, NOT_PDF, filename='invoice.pdf')
    assert response.status_code == 400


def test_convert_wrong_magic_bytes_has_error_field(client):
    data = _upload_pdf(client, NOT_PDF, filename='invoice.pdf').get_json()
    assert 'error' in data


# ── Success: output=json ───────────────────────────────────────────────────────
# Используем invoice_app_module фикстуру (из conftest) для патчинга модуля app.py,
# загруженного через importlib как '_invoice_main' (обход конфликта app.py vs app/ пакет).

def test_convert_json_output_returns_200(client, monkeypatch, invoice_app_module):
    monkeypatch.setattr(invoice_app_module, 'extract_invoice', lambda *a, **kw: (SAMPLE_INVOICE, False))
    monkeypatch.setattr(invoice_app_module, 'validate_invoice_data', lambda d: [])
    response = _upload_pdf(client, MINIMAL_PDF, extra={'output': 'json'})
    assert response.status_code == 200


def test_convert_json_output_returns_json_content_type(client, monkeypatch, invoice_app_module):
    monkeypatch.setattr(invoice_app_module, 'extract_invoice', lambda *a, **kw: (SAMPLE_INVOICE, False))
    monkeypatch.setattr(invoice_app_module, 'validate_invoice_data', lambda d: [])
    response = _upload_pdf(client, MINIMAL_PDF, extra={'output': 'json'})
    assert 'application/json' in response.content_type


def test_convert_json_output_returns_invoice_data(client, monkeypatch, invoice_app_module):
    monkeypatch.setattr(invoice_app_module, 'extract_invoice', lambda *a, **kw: (SAMPLE_INVOICE, False))
    monkeypatch.setattr(invoice_app_module, 'validate_invoice_data', lambda d: [])
    response = _upload_pdf(client, MINIMAL_PDF, extra={'output': 'json'})
    data = response.get_json()
    assert data['invoice_number'] == '123'


def test_convert_json_output_has_x_vision_fallback_header(client, monkeypatch, invoice_app_module):
    monkeypatch.setattr(invoice_app_module, 'extract_invoice', lambda *a, **kw: (SAMPLE_INVOICE, False))
    monkeypatch.setattr(invoice_app_module, 'validate_invoice_data', lambda d: [])
    response = _upload_pdf(client, MINIMAL_PDF, extra={'output': 'json'})
    assert 'X-Vision-Fallback' in response.headers


def test_convert_json_output_vision_fallback_is_false_when_not_used(client, monkeypatch, invoice_app_module):
    monkeypatch.setattr(invoice_app_module, 'extract_invoice', lambda *a, **kw: (SAMPLE_INVOICE, False))
    monkeypatch.setattr(invoice_app_module, 'validate_invoice_data', lambda d: [])
    response = _upload_pdf(client, MINIMAL_PDF, extra={'output': 'json'})
    assert response.headers['X-Vision-Fallback'] == 'false'


def test_convert_json_output_vision_fallback_is_true_when_used(client, monkeypatch, invoice_app_module):
    monkeypatch.setattr(invoice_app_module, 'extract_invoice', lambda *a, **kw: (SAMPLE_INVOICE, True))
    monkeypatch.setattr(invoice_app_module, 'validate_invoice_data', lambda d: [])
    response = _upload_pdf(client, MINIMAL_PDF, extra={'output': 'json'})
    assert response.headers['X-Vision-Fallback'] == 'true'


def test_convert_json_output_has_x_parse_quality_header(client, monkeypatch, invoice_app_module):
    monkeypatch.setattr(invoice_app_module, 'extract_invoice', lambda *a, **kw: (SAMPLE_INVOICE, False))
    monkeypatch.setattr(invoice_app_module, 'validate_invoice_data', lambda d: [])
    response = _upload_pdf(client, MINIMAL_PDF, extra={'output': 'json'})
    assert 'X-Parse-Quality' in response.headers


def test_convert_json_output_parse_quality_ok_when_no_warnings(client, monkeypatch, invoice_app_module):
    monkeypatch.setattr(invoice_app_module, 'extract_invoice', lambda *a, **kw: (SAMPLE_INVOICE, False))
    monkeypatch.setattr(invoice_app_module, 'validate_invoice_data', lambda d: [])
    response = _upload_pdf(client, MINIMAL_PDF, extra={'output': 'json'})
    assert response.headers['X-Parse-Quality'] == 'ok'


def test_convert_json_output_parse_quality_partial_when_warnings(client, monkeypatch, invoice_app_module):
    monkeypatch.setattr(invoice_app_module, 'extract_invoice', lambda *a, **kw: (SAMPLE_INVOICE, False))
    monkeypatch.setattr(invoice_app_module, 'validate_invoice_data', lambda d: ['Some warning'])
    response = _upload_pdf(client, MINIMAL_PDF, extra={'output': 'json'})
    assert response.headers['X-Parse-Quality'] == 'partial'


def test_convert_json_output_invoice_contains_items(client, monkeypatch, invoice_app_module):
    monkeypatch.setattr(invoice_app_module, 'extract_invoice', lambda *a, **kw: (SAMPLE_INVOICE, False))
    monkeypatch.setattr(invoice_app_module, 'validate_invoice_data', lambda d: [])
    response = _upload_pdf(client, MINIMAL_PDF, extra={'output': 'json'})
    data = response.get_json()
    assert len(data['items']) == 1


def test_convert_json_output_invoice_has_supplier(client, monkeypatch, invoice_app_module):
    monkeypatch.setattr(invoice_app_module, 'extract_invoice', lambda *a, **kw: (SAMPLE_INVOICE, False))
    monkeypatch.setattr(invoice_app_module, 'validate_invoice_data', lambda d: [])
    response = _upload_pdf(client, MINIMAL_PDF, extra={'output': 'json'})
    data = response.get_json()
    assert data['supplier']['name'] == 'ООО Поставщик'
