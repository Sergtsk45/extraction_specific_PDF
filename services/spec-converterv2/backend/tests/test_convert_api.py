"""Tests for POST /convert endpoint of spec-converterv2."""

import io
import os
import openpyxl


MINIMAL_PDF = b"%PDF-1.4\n1 0 obj<</Type /Catalog>>endobj\n%%EOF\n"
NOT_PDF = b"PK\x03\x04fake zip content here"

SAMPLE_PAGES_DATA = [
    {
        'sheet_name': 'В1-3',
        'page_num': 1,
        'rows': [
            ['Позиция', 'Наименование', 'Тип', 'Код', 'Завод', 'Ед.', 'Кол.', 'Масса', 'Примечание'],
            ['1', 'Труба', 'PN20', '', 'Завод', 'м', '10', '0,5', ''],
        ],
    }
]


def _upload_pdf(client, content: bytes, filename: str = 'spec.pdf', extra: dict = None):
    data = {'file': (io.BytesIO(content), filename)}
    if extra:
        data.update(extra)
    return client.post('/convert', data=data, content_type='multipart/form-data')


# ── Validation errors ──────────────────────────────────────────────────────────

def test_convert_returns_400_when_no_file(client):
    response = client.post('/convert', data={}, content_type='multipart/form-data')
    assert response.status_code == 400


def test_convert_no_file_code_is_no_file(client):
    response = client.post('/convert', data={}, content_type='multipart/form-data')
    data = response.get_json()
    assert data['code'] == 'NO_FILE'


def test_convert_returns_400_for_wrong_extension(client):
    response = _upload_pdf(client, MINIMAL_PDF, filename='spec.docx')
    assert response.status_code == 400


def test_convert_wrong_extension_code_is_invalid_type(client):
    response = _upload_pdf(client, MINIMAL_PDF, filename='spec.docx')
    data = response.get_json()
    assert data['code'] == 'INVALID_TYPE'


def test_convert_returns_400_for_wrong_magic_bytes(client):
    response = _upload_pdf(client, NOT_PDF, filename='spec.pdf')
    assert response.status_code == 400


def test_convert_wrong_magic_bytes_code_is_invalid_file(client):
    response = _upload_pdf(client, NOT_PDF, filename='spec.pdf')
    data = response.get_json()
    assert data['code'] == 'INVALID_FILE'


# ── Empty result ───────────────────────────────────────────────────────────────

def test_convert_returns_500_when_process_pdf_returns_empty(client, monkeypatch):
    monkeypatch.setattr('app.process_pdf', lambda *a, **kw: ([], False))
    response = _upload_pdf(client, MINIMAL_PDF)
    assert response.status_code == 500


def test_convert_empty_result_code_is_empty_result(client, monkeypatch):
    monkeypatch.setattr('app.process_pdf', lambda *a, **kw: ([], False))
    response = _upload_pdf(client, MINIMAL_PDF)
    data = response.get_json()
    assert data['code'] == 'EMPTY_RESULT'


# ── Success ────────────────────────────────────────────────────────────────────

def _make_create_excel(tmp_path):
    """Return a _create_excel replacement that writes a real minimal xlsx."""
    def fake_create_excel(pages_data, output_path):
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = 'В1-3'
        ws.append(['Позиция', 'Наименование'])
        ws.append(['1', 'Труба'])
        wb.save(output_path)
        return ['В1-3']
    return fake_create_excel


def test_convert_returns_200_on_success(client, monkeypatch, tmp_path):
    monkeypatch.setattr('app.process_pdf', lambda *a, **kw: (SAMPLE_PAGES_DATA, False))
    monkeypatch.setattr('app._create_excel', _make_create_excel(tmp_path))
    monkeypatch.setattr('app.OUTPUT_FOLDER', str(tmp_path))
    response = _upload_pdf(client, MINIMAL_PDF)
    assert response.status_code == 200


def test_convert_success_response_is_xlsx(client, monkeypatch, tmp_path):
    monkeypatch.setattr('app.process_pdf', lambda *a, **kw: (SAMPLE_PAGES_DATA, False))
    monkeypatch.setattr('app._create_excel', _make_create_excel(tmp_path))
    monkeypatch.setattr('app.OUTPUT_FOLDER', str(tmp_path))
    response = _upload_pdf(client, MINIMAL_PDF)
    assert 'spreadsheetml' in response.content_type


def test_convert_success_has_vision_fallback_header(client, monkeypatch, tmp_path):
    monkeypatch.setattr('app.process_pdf', lambda *a, **kw: (SAMPLE_PAGES_DATA, False))
    monkeypatch.setattr('app._create_excel', _make_create_excel(tmp_path))
    monkeypatch.setattr('app.OUTPUT_FOLDER', str(tmp_path))
    response = _upload_pdf(client, MINIMAL_PDF)
    assert 'X-Vision-Fallback' in response.headers


def test_convert_success_vision_fallback_is_false_when_not_used(client, monkeypatch, tmp_path):
    monkeypatch.setattr('app.process_pdf', lambda *a, **kw: (SAMPLE_PAGES_DATA, False))
    monkeypatch.setattr('app._create_excel', _make_create_excel(tmp_path))
    monkeypatch.setattr('app.OUTPUT_FOLDER', str(tmp_path))
    response = _upload_pdf(client, MINIMAL_PDF)
    assert response.headers['X-Vision-Fallback'] == 'false'


def test_convert_success_vision_fallback_is_true_when_used(client, monkeypatch, tmp_path):
    monkeypatch.setattr('app.process_pdf', lambda *a, **kw: (SAMPLE_PAGES_DATA, True))
    monkeypatch.setattr('app._create_excel', _make_create_excel(tmp_path))
    monkeypatch.setattr('app.OUTPUT_FOLDER', str(tmp_path))
    response = _upload_pdf(client, MINIMAL_PDF)
    assert response.headers['X-Vision-Fallback'] == 'true'


def test_convert_success_has_sheet_names_header(client, monkeypatch, tmp_path):
    monkeypatch.setattr('app.process_pdf', lambda *a, **kw: (SAMPLE_PAGES_DATA, False))
    monkeypatch.setattr('app._create_excel', _make_create_excel(tmp_path))
    monkeypatch.setattr('app.OUTPUT_FOLDER', str(tmp_path))
    response = _upload_pdf(client, MINIMAL_PDF)
    assert 'X-Sheet-Names' in response.headers
