"""
app/validators.py
Арифметическая валидация данных счёта.
"""
from __future__ import annotations

EPSILON = 1.0  # допустимая погрешность в рублях


def validate_invoice_data(data: dict) -> list[str]:
    """
    Возвращает список предупреждений (warnings).
    Пустой список — всё ОК.
    """
    warnings: list[str] = []
    items = data.get("items", [])
    totals = data.get("totals", {})

    if not items:
        warnings.append("Не найдено ни одной строки товаров/услуг")
        return warnings

    # 1. qty × price ≈ amount_w_vat (по строкам)
    for i, item in enumerate(items, 1):
        qty   = _num(item.get("qty"))
        price = _num(item.get("price"))
        amt   = _num(item.get("amount_w_vat")) or _num(item.get("amount_wo_vat"))

        if qty and price and amt:
            expected = round(qty * price, 2)
            if abs(expected - amt) > EPSILON * max(1, abs(amt) / 1000):
                warnings.append(
                    f"Строка {i} ({item.get('name', '')[:40]}): "
                    f"кол-во×цена={expected:.2f} ≠ сумма={amt:.2f}"
                )

    # 2. Сумма строк ≈ итого к оплате
    total_w_vat = _num(totals.get("total_w_vat"))
    if total_w_vat:
        sum_items = sum(
            _num(it.get("amount_w_vat")) or _num(it.get("amount_wo_vat"))
            for it in items
            if _num(it.get("amount_w_vat")) or _num(it.get("amount_wo_vat"))
        )
        if sum_items and abs(sum_items - total_w_vat) > EPSILON:
            warnings.append(
                f"Сумма строк ({sum_items:.2f}) ≠ итого к оплате ({total_w_vat:.2f})"
            )

    # 3. НДС + сумма без НДС ≈ итого
    vat_total    = _num(totals.get("vat_total"))
    total_wo_vat = _num(totals.get("total_wo_vat"))
    if vat_total and total_wo_vat and total_w_vat:
        expected_total = round(vat_total + total_wo_vat, 2)
        if abs(expected_total - total_w_vat) > EPSILON:
            warnings.append(
                f"Итого без НДС ({total_wo_vat:.2f}) + НДС ({vat_total:.2f}) "
                f"= {expected_total:.2f} ≠ к оплате ({total_w_vat:.2f})"
            )

    return warnings


def _num(value) -> float:
    if value is None or value == "":
        return 0.0
    try:
        return float(value)
    except (ValueError, TypeError):
        return 0.0
