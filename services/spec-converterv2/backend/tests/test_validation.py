"""Tests for _validate_pdf and _safe_filename internal functions in spec-converterv2."""

import io
from unittest.mock import MagicMock

from app import _validate_pdf, _safe_filename


def _make_file_storage(filename: str, content: bytes):
    """Helper: create a minimal file storage mock."""
    mock = MagicMock()
    mock.filename = filename
    buf = io.BytesIO(content)
    mock.read = buf.read
    mock.seek = buf.seek
    return mock


# ── _validate_pdf ──────────────────────────────────────────────────────────────

def test_validate_pdf_returns_true_for_valid_pdf():
    fs = _make_file_storage('spec.pdf', b'%PDF-1.4\nsome content')
    valid, err = _validate_pdf(fs)
    assert valid is True


def test_validate_pdf_returns_none_error_for_valid_pdf():
    fs = _make_file_storage('spec.pdf', b'%PDF-1.4\nsome content')
    valid, err = _validate_pdf(fs)
    assert err is None


def test_validate_pdf_returns_false_for_non_pdf_extension():
    fs = _make_file_storage('spec.docx', b'%PDF-1.4\nsome content')
    valid, err = _validate_pdf(fs)
    assert valid is False


def test_validate_pdf_returns_error_message_for_non_pdf_extension():
    fs = _make_file_storage('spec.docx', b'%PDF-1.4\nsome content')
    valid, err = _validate_pdf(fs)
    assert err is not None
    assert len(err) > 0


def test_validate_pdf_returns_false_for_wrong_magic_bytes():
    fs = _make_file_storage('spec.pdf', b'PK\x03\x04fake zip content here')
    valid, err = _validate_pdf(fs)
    assert valid is False


def test_validate_pdf_returns_error_message_for_wrong_magic_bytes():
    fs = _make_file_storage('spec.pdf', b'PK\x03\x04fake zip content here')
    valid, err = _validate_pdf(fs)
    assert err is not None
    assert len(err) > 0


def test_validate_pdf_resets_stream_position_after_read():
    """Ensure stream position is 0 after validation so file can be read again."""
    content = b'%PDF-1.4\nsome content'
    buf = io.BytesIO(content)
    mock = __import__('unittest.mock', fromlist=['MagicMock']).MagicMock()
    mock.filename = 'spec.pdf'
    mock.read = buf.read
    mock.seek = buf.seek
    from app import _validate_pdf
    _validate_pdf(mock)
    assert buf.tell() == 0


# ── _safe_filename ─────────────────────────────────────────────────────────────

def test_safe_filename_ends_with_pdf_for_cyrillic():
    result = _safe_filename('Спецификация.pdf')
    assert result.endswith('.pdf')


def test_safe_filename_contains_underscore_separator():
    result = _safe_filename('Спецификация.pdf')
    assert '_' in result


def test_safe_filename_is_unique_between_calls():
    first = _safe_filename('Спецификация.pdf')
    second = _safe_filename('Спецификация.pdf')
    assert first != second


def test_safe_filename_ends_with_pdf_for_ascii():
    result = _safe_filename('test.pdf')
    assert result.endswith('.pdf')


def test_safe_filename_has_uuid_prefix():
    """UUID hex prefix is 12 chars followed by underscore."""
    result = _safe_filename('test.pdf')
    prefix = result.split('_')[0]
    assert len(prefix) == 12


def test_safe_filename_non_empty():
    result = _safe_filename('document.pdf')
    assert len(result) > 0
