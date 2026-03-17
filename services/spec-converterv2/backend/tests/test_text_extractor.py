"""Tests for pure functions in pdf_text_extractor.py."""

from pdf_text_extractor import (
    fix_encoding,
    needs_encoding_fix,
    find_column_mapping,
    detect_sheet_name,
    _merge_continuation_rows,
    _is_stamp_row,
)


# ── needs_encoding_fix ─────────────────────────────────────────────────────────

def test_needs_encoding_fix_returns_true_for_latin1_artifacts():
    # "Ïîçèöèÿ" is "Позиция" encoded as CP1251 but read as Latin1
    assert needs_encoding_fix("Ïîçèöèÿ") is True


def test_needs_encoding_fix_returns_false_for_clean_cyrillic():
    assert needs_encoding_fix("Позиция") is False


def test_needs_encoding_fix_returns_false_for_empty_string():
    assert needs_encoding_fix("") is False


def test_needs_encoding_fix_returns_false_for_ascii():
    assert needs_encoding_fix("Hello World 123") is False


def test_needs_encoding_fix_returns_true_for_single_artifact_char():
    # A single char in the 0xC0-0xFF range is enough
    assert needs_encoding_fix("À") is True


# ── fix_encoding ───────────────────────────────────────────────────────────────

def test_fix_encoding_converts_latin1_artifact_to_cyrillic():
    # "Ïîçèöèÿ" → "Позиция"
    result = fix_encoding("Ïîçèöèÿ")
    assert result == "Позиция"


def test_fix_encoding_leaves_clean_cyrillic_unchanged():
    text = "Позиция"
    result = fix_encoding(text)
    assert result == text


def test_fix_encoding_leaves_empty_string_unchanged():
    result = fix_encoding("")
    assert result == ""


def test_fix_encoding_leaves_ascii_unchanged():
    text = "Hello"
    result = fix_encoding(text)
    assert result == text


# ── find_column_mapping ────────────────────────────────────────────────────────

def test_find_column_mapping_returns_dict_for_standard_row():
    # A row with exactly digits 1-9 in order (9 non-empty cells)
    table = [
        [None, "1", "2", "3", "4", "5", "6", "7", "8", "9"],
    ]
    result = find_column_mapping(table)
    assert result is not None


def test_find_column_mapping_maps_all_nine_digits():
    table = [
        [None, "1", "2", "3", "4", "5", "6", "7", "8", "9"],
    ]
    result = find_column_mapping(table)
    assert set(result.values()) == {1, 2, 3, 4, 5, 6, 7, 8, 9}


def test_find_column_mapping_returns_none_when_no_digit_row():
    table = [
        ["Позиция", "Наименование", "Тип", "Код", "Завод", "Ед.", "Кол.", "Масса", "Примечание"],
        ["1", "Труба полипропиленовая", "", "", "", "м", "10", "", ""],
    ]
    result = find_column_mapping(table)
    assert result is None


def test_find_column_mapping_returns_none_for_empty_table():
    result = find_column_mapping([])
    assert result is None


def test_find_column_mapping_finds_row_within_first_five_rows():
    table = [
        ["Заголовок", "таблицы", "спецификации", "", "", "", "", "", ""],
        [None, "1", "2", "3", "4", "5", "6", "7", "8", "9"],
    ]
    result = find_column_mapping(table)
    assert result is not None


# ── detect_sheet_name ──────────────────────────────────────────────────────────

def test_detect_sheet_name_extracts_v_system_code():
    rows = [
        ["В1-3", "Водопровод холодный", "", "", "", "", "", "", ""],
        ["1", "Труба", "", "", "", "м", "10", "", ""],
    ]
    result = detect_sheet_name(rows, 1)
    assert result == "В1-3"


def test_detect_sheet_name_extracts_t_system_codes():
    rows = [
        ["Т3, Т4", "Горячее водоснабжение", "", "", "", "", "", "", ""],
        ["1", "Полотенцесушитель", "", "", "", "шт", "4", "", ""],
    ]
    result = detect_sheet_name(rows, 1)
    # Should find a system code like "Т3" or "Т3, Т4"
    assert "Т" in result or "T" in result


def test_detect_sheet_name_returns_default_when_no_system_code():
    rows = [
        ["", "Разные материалы", "", "", "", "", "", "", ""],
        ["1", "Труба", "", "", "", "м", "10", "", ""],
    ]
    result = detect_sheet_name(rows, 3)
    assert result == "Спецификация стр.3"


def test_detect_sheet_name_uses_page_num_in_default():
    rows = [["", "Материалы", "", "", "", "", "", "", ""]]
    result = detect_sheet_name(rows, 5)
    assert "5" in result


# ── _is_stamp_row ──────────────────────────────────────────────────────────────

def test_is_stamp_row_returns_true_for_stamp_keywords():
    row_text = "изм. подп. формат"
    mapped_row = ["изм.", "подп.", "формат", "", "", "", "", "", ""]
    assert _is_stamp_row(row_text, mapped_row) is True


def test_is_stamp_row_returns_false_for_product_row():
    row_text = "труба полипропиленовая"
    mapped_row = ["1", "Труба полипропиленовая", "PN20", "", "Завод", "м", "10", "0,5", ""]
    assert _is_stamp_row(row_text, mapped_row) is False


def test_is_stamp_row_returns_true_for_developer_keyword():
    row_text = "разработал иванов"
    mapped_row = ["разработал", "Иванов", "", "", "", "", "", "", ""]
    assert _is_stamp_row(row_text, mapped_row) is True


def test_is_stamp_row_returns_false_for_empty_row():
    assert _is_stamp_row("", ["", "", "", "", "", "", "", "", ""]) is False


# ── _merge_continuation_rows ───────────────────────────────────────────────────

def test_merge_continuation_rows_merges_text_only_continuation():
    """Second row has no position and only text in col[1] → merges into first."""
    rows = [
        ["1", "Труба полипропиленовая", "", "", "", "м", "10", "", ""],
        ["",  "продолжение наименования", "", "", "", "", "", "", ""],
    ]
    result = _merge_continuation_rows(rows)
    assert len(result) == 1


def test_merge_continuation_rows_merged_text_appended():
    rows = [
        ["1", "Труба полипропиленовая", "", "", "", "м", "10", "", ""],
        ["",  "продолжение наименования", "", "", "", "", "", "", ""],
    ]
    result = _merge_continuation_rows(rows)
    assert "продолжение наименования" in result[0][1]


def test_merge_continuation_rows_does_not_merge_row_with_qty():
    """Row with quantity data is NOT a continuation — it stays separate."""
    rows = [
        ["1", "Труба полипропиленовая", "", "", "", "м", "10", "", ""],
        ["",  "Кран шаровой", "", "", "", "шт", "5", "", ""],
    ]
    result = _merge_continuation_rows(rows)
    assert len(result) == 2


def test_merge_continuation_rows_does_not_merge_subposition():
    """Row starting with dash in col[1] is a sub-position, not continuation."""
    rows = [
        ["1", "Водомерный узел в т.ч.:", "", "", "", "", "", "", ""],
        ["",  "-задвижка фланцевая", "", "", "", "шт", "2", "", ""],
    ]
    result = _merge_continuation_rows(rows)
    assert len(result) == 2


def test_merge_continuation_rows_single_row_unchanged():
    rows = [["1", "Труба", "", "", "", "м", "10", "", ""]]
    result = _merge_continuation_rows(rows)
    assert len(result) == 1


def test_merge_continuation_rows_returns_original_when_less_than_two():
    rows = []
    result = _merge_continuation_rows(rows)
    assert result == []
