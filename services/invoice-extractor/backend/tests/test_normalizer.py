"""Tests for pure functions in app/normalizer.py."""

from app.normalizer import normalize_invoice, _to_float, _normalize_vat_rate, _normalize_date_str


# ── _to_float ──────────────────────────────────────────────────────────────────

def test_to_float_converts_space_separated_thousands_with_comma():
    assert _to_float("1 234,56") == 1234.56


def test_to_float_returns_empty_string_for_empty_input():
    assert _to_float("") == ""


def test_to_float_converts_int_to_float():
    assert _to_float(100) == 100.0


def test_to_float_returns_float_for_plain_float():
    assert _to_float(3.14) == 3.14


def test_to_float_returns_empty_string_for_non_numeric():
    assert _to_float("abc") == ""


def test_to_float_returns_empty_string_for_none():
    assert _to_float(None) == ""


def test_to_float_converts_string_with_dot():
    assert _to_float("100.50") == 100.5


# ── _normalize_vat_rate ────────────────────────────────────────────────────────

def test_normalize_vat_rate_preserves_percent_sign():
    assert _normalize_vat_rate("20%") == "20%"


def test_normalize_vat_rate_extracts_number_and_adds_percent():
    assert _normalize_vat_rate("20") == "20%"


def test_normalize_vat_rate_handles_bez_nds():
    assert _normalize_vat_rate("без НДС") == "без НДС"


def test_normalize_vat_rate_converts_zero_to_bez_nds():
    assert _normalize_vat_rate("0") == "без НДС"


def test_normalize_vat_rate_converts_dash_to_bez_nds():
    assert _normalize_vat_rate("-") == "без НДС"


def test_normalize_vat_rate_returns_empty_for_empty_input():
    assert _normalize_vat_rate("") == ""


def test_normalize_vat_rate_handles_ne_oblagaetsya():
    assert _normalize_vat_rate("не облагается") == "без НДС"


# ── _normalize_date_str ────────────────────────────────────────────────────────

def test_normalize_date_str_converts_russian_month_name():
    assert _normalize_date_str("29 января 2026 г.") == "2026-01-29"


def test_normalize_date_str_leaves_iso_date_unchanged():
    assert _normalize_date_str("2026-01-29") == "2026-01-29"


def test_normalize_date_str_returns_empty_for_empty():
    assert _normalize_date_str("") == ""


def test_normalize_date_str_converts_december():
    assert _normalize_date_str("31 декабря 2025 г.") == "2025-12-31"


def test_normalize_date_str_pads_single_digit_day():
    result = _normalize_date_str("5 марта 2026 г.")
    assert result == "2026-03-05"


# ── normalize_invoice ──────────────────────────────────────────────────────────

def _make_invoice(**overrides):
    base = {
        "document_type": "supplier_invoice",
        "invoice_number": "123",
        "invoice_date": "29 января 2026 г.",
        "supplier": {
            "name": "  ООО Поставщик  ",
            "inn": "12-34-56-78-90",
            "kpp": "123 456 789",
            "address": "г. Москва",
            "bank": {
                "name": "Банк",
                "bik": "044-525-001",
                "account": "407 028 100 000 000 000 01",
                "corr_account": "301 018 100 000 000 000 01",
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
                "article": "A001",
                "name": "  Товар 1  ",
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
    }
    base.update(overrides)
    return base


def test_normalize_invoice_assigns_line_no_to_items():
    invoice = _make_invoice()
    result = normalize_invoice(invoice)
    assert result["items"][0]["line_no"] == 1


def test_normalize_invoice_strips_whitespace_from_item_name():
    invoice = _make_invoice()
    result = normalize_invoice(invoice)
    assert result["items"][0]["name"] == "Товар 1"


def test_normalize_invoice_strips_whitespace_from_supplier_name():
    invoice = _make_invoice()
    result = normalize_invoice(invoice)
    assert result["supplier"]["name"] == "ООО Поставщик"


def test_normalize_invoice_converts_inn_to_digits_only():
    invoice = _make_invoice()
    result = normalize_invoice(invoice)
    assert result["supplier"]["inn"] == "1234567890"


def test_normalize_invoice_converts_kpp_to_digits_only():
    invoice = _make_invoice()
    result = normalize_invoice(invoice)
    assert result["supplier"]["kpp"] == "123456789"


def test_normalize_invoice_converts_bik_to_digits_only():
    invoice = _make_invoice()
    result = normalize_invoice(invoice)
    assert result["supplier"]["bank"]["bik"] == "044525001"


def test_normalize_invoice_converts_account_to_digits_only():
    invoice = _make_invoice()
    result = normalize_invoice(invoice)
    assert result["supplier"]["bank"]["account"] == "40702810000000000001"


def test_normalize_invoice_normalizes_invoice_date():
    invoice = _make_invoice()
    result = normalize_invoice(invoice)
    assert result["invoice_date"] == "2026-01-29"


def test_normalize_invoice_normalizes_vat_rate_in_items():
    invoice = _make_invoice()
    result = normalize_invoice(invoice)
    assert result["items"][0]["vat_rate"] == "20%"


def test_normalize_invoice_converts_totals_to_float():
    invoice = _make_invoice()
    result = normalize_invoice(invoice)
    assert isinstance(result["totals"]["total_w_vat"], float)


def test_normalize_invoice_assigns_sequential_line_nos():
    invoice = _make_invoice()
    invoice["items"] = [
        {"name": "Товар 1", "qty": 1.0, "price": 100.0, "amount_w_vat": 100.0},
        {"name": "Товар 2", "qty": 2.0, "price": 50.0, "amount_w_vat": 100.0},
    ]
    result = normalize_invoice(invoice)
    assert result["items"][0]["line_no"] == 1
    assert result["items"][1]["line_no"] == 2
