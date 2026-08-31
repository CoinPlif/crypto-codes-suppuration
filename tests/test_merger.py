"""Тесты логики склейки. Файлы собираются в памяти, примеры из репозитория не нужны."""

from __future__ import annotations

import sys
from io import BytesIO
from pathlib import Path

import pandas as pd
import pytest
from openpyxl import Workbook

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from merger import (  # noqa: E402 — путь к пакету добавляется выше
    OLE2_SIGNATURE,
    detect_engine,
    drop_duplicate_codes,
    merge_tables,
    read_table,
    to_xlsx_bytes,
)

GTIN = "04688749270197"
PRODUCT = "РБКУ SS Фо Хо лапша рисовая (пакет 200г) 24"


def make_xlsx(rows: list[list[str]]) -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    for row in rows:
        sheet.append(row)
    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def code_rows(prefix: str, count: int) -> list[list[str]]:
    return [[f"010468874927019721{prefix}{index}", GTIN, PRODUCT] for index in range(count)]


def test_detect_engine_recognises_xlsx():
    assert detect_engine(make_xlsx(code_rows("a", 1))) == "openpyxl"


def test_detect_engine_recognises_legacy_xls():
    assert detect_engine(OLE2_SIGNATURE + b"\x00" * 16) == "xlrd"


def test_detect_engine_rejects_garbage():
    with pytest.raises(ValueError):
        detect_engine(b"not a spreadsheet")


def test_xlsx_saved_under_xls_extension_is_read():
    """Регрессия на реальную выгрузку: имя `.xls`, содержимое — xlsx."""
    frame = read_table("order_2.xls", make_xlsx(code_rows("a", 3)))
    assert frame.shape == (3, 3)


def test_merge_concatenates_rows_in_order():
    first = read_table("a.xlsx", make_xlsx(code_rows("a", 3)))
    second = read_table("b.xlsx", make_xlsx(code_rows("b", 4)))

    merged, warnings = merge_tables([("a.xlsx", first), ("b.xlsx", second)])

    assert merged.shape == (7, 3)
    assert warnings == []
    assert merged.iloc[0, 0].endswith("a0")
    assert merged.iloc[3, 0].endswith("b0")


def test_gtin_leading_zero_survives_roundtrip():
    """Главный тест: ноль в начале GTIN не должен потеряться нигде в цикле."""
    first = read_table("a.xlsx", make_xlsx(code_rows("a", 2)))
    second = read_table("b.xlsx", make_xlsx(code_rows("b", 2)))
    merged, _ = merge_tables([("a.xlsx", first), ("b.xlsx", second)])

    restored = read_table("merged.xlsx", to_xlsx_bytes(merged))

    assert len(restored) == 4
    assert restored[1].tolist() == [GTIN] * 4


def test_mismatched_column_count_is_padded_and_reported():
    narrow = read_table("narrow.xlsx", make_xlsx([["code-1", GTIN, PRODUCT]]))
    wide = read_table("wide.xlsx", make_xlsx([["code-2", GTIN, PRODUCT, "экстра"]]))

    merged, warnings = merge_tables([("narrow.xlsx", narrow), ("wide.xlsx", wide)])

    assert merged.shape == (2, 4)
    assert merged.iloc[0, 3] == ""
    assert merged.iloc[1, 3] == "экстра"
    assert len(warnings) == 1
    assert "narrow.xlsx" in warnings[0]


def test_drop_duplicate_codes_keeps_first_occurrence():
    frame = pd.DataFrame(
        [["code-1", GTIN], ["code-2", GTIN], ["code-1", GTIN]],
    )

    cleaned, removed = drop_duplicate_codes(frame)

    assert removed == 1
    assert cleaned[0].tolist() == ["code-1", "code-2"]
