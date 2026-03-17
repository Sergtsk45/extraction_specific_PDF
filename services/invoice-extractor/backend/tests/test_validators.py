"""Tests for validate_invoice_data in app/validators.py."""

from app.validators import validate_invoice_data


def _make_item(line_no=1, name="Товар 1", qty=10.0, price=100.0,
               amount_wo_vat=1000.0, vat_rate="20", vat_amount=200.0,
               amount_w_vat=1200.0):
    return {
        "line_no": line_no,
        "name": name,
        "qty": qty,
        "price": price,
        "amount_wo_vat": amount_wo_vat,
        "vat_rate": vat_rate,
        "vat_amount": vat_amount,
        "amount_w_vat": amount_w_vat,
    }


def _make_totals(total_wo_vat=1000.0, vat_total=200.0, total_w_vat=1200.0):
    return {
        "total_wo_vat": total_wo_vat,
        "vat_total": vat_total,
        "total_w_vat": total_w_vat,
    }


# ── Empty items ────────────────────────────────────────────────────────────────

def test_empty_items_returns_warning():
    result = validate_invoice_data({"items": [], "totals": {}})
    assert len(result) > 0


def test_empty_items_warning_contains_not_found_text():
    result = validate_invoice_data({"items": [], "totals": {}})
    assert any("Не найдено" in w for w in result)


# ── Valid item: qty × price == amount_w_vat ────────────────────────────────────

def test_valid_item_produces_no_row_warning():
    item = _make_item(qty=10.0, price=100.0, amount_w_vat=1200.0)
    data = {"items": [item], "totals": _make_totals()}
    warnings = validate_invoice_data(data)
    row_warnings = [w for w in warnings if "Строка 1" in w]
    assert len(row_warnings) == 0


# ── Row mismatch warning ───────────────────────────────────────────────────────

def test_mismatch_qty_price_amount_produces_warning():
    # qty=2, price=100.0, amount_w_vat=300.0 → expected=200.0 ≠ 300.0
    item = _make_item(qty=2, price=100.0, amount_w_vat=300.0)
    data = {"items": [item], "totals": _make_totals(total_w_vat=300.0)}
    warnings = validate_invoice_data(data)
    row_warnings = [w for w in warnings if "Строка 1" in w]
    assert len(row_warnings) == 1


def test_mismatch_warning_mentions_row_number():
    item = _make_item(qty=2, price=100.0, amount_w_vat=300.0)
    data = {"items": [item], "totals": _make_totals(total_w_vat=300.0)}
    warnings = validate_invoice_data(data)
    assert any("Строка 1" in w for w in warnings)


# ── Total sum matches ──────────────────────────────────────────────────────────

def test_correct_total_sum_produces_no_total_warning():
    item = _make_item(qty=10.0, price=100.0, amount_w_vat=1200.0)
    data = {"items": [item], "totals": _make_totals(total_w_vat=1200.0)}
    warnings = validate_invoice_data(data)
    total_warnings = [w for w in warnings if "Сумма строк" in w]
    assert len(total_warnings) == 0


# ── Total sum mismatch ─────────────────────────────────────────────────────────

def test_total_sum_mismatch_produces_warning():
    item = _make_item(qty=10.0, price=100.0, amount_w_vat=1200.0)
    # Claim total is 999.0 while sum of items is 1200.0
    data = {"items": [item], "totals": _make_totals(total_w_vat=999.0)}
    warnings = validate_invoice_data(data)
    total_warnings = [w for w in warnings if "Сумма строк" in w or "итого к оплате" in w.lower()]
    assert len(total_warnings) >= 1


def test_total_sum_mismatch_warning_contains_both_values():
    item = _make_item(qty=10.0, price=100.0, amount_w_vat=1200.0)
    data = {"items": [item], "totals": _make_totals(total_w_vat=999.0)}
    warnings = validate_invoice_data(data)
    total_warning = next((w for w in warnings if "Сумма строк" in w), None)
    assert total_warning is not None
    assert "1200" in total_warning
    assert "999" in total_warning


# ── VAT check ─────────────────────────────────────────────────────────────────

def test_vat_check_no_warning_when_correct():
    # 1000 + 200 = 1200 ✓
    item = _make_item(qty=10.0, price=100.0, amount_w_vat=1200.0)
    data = {"items": [item], "totals": _make_totals(total_wo_vat=1000.0, vat_total=200.0, total_w_vat=1200.0)}
    warnings = validate_invoice_data(data)
    vat_warnings = [w for w in warnings if "НДС" in w and "Итого" in w]
    assert len(vat_warnings) == 0


def test_vat_check_produces_warning_when_totals_inconsistent():
    # total_wo_vat(1000) + vat_total(200) = 1200, but total_w_vat=1500 → mismatch
    item = _make_item(qty=10.0, price=100.0, amount_w_vat=1500.0)
    data = {
        "items": [item],
        "totals": _make_totals(total_wo_vat=1000.0, vat_total=200.0, total_w_vat=1500.0),
    }
    warnings = validate_invoice_data(data)
    vat_warnings = [w for w in warnings if "НДС" in w]
    assert len(vat_warnings) >= 1
