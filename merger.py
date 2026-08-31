"""Чтение, склейка и выгрузка Excel-файлов с кодами маркировки.

Шапки в файлах нет: первая строка — уже данные, столбцы сопоставляются по позиции.
"""

from __future__ import annotations

from io import BytesIO

import pandas as pd
from openpyxl import Workbook

ZIP_SIGNATURE = b"PK\x03\x04"
OLE2_SIGNATURE = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"

#: Колонка с кодом DataMatrix — по ней считаются дубликаты.
CODE_COLUMN = 0


def detect_engine(data: bytes) -> str:
    """Подобрать движок pandas по сигнатуре файла.

    Расширению верить нельзя: выгрузки заказов приходят с именем `.xls`,
    хотя внутри лежит обычный xlsx (zip).
    """
    if data.startswith(ZIP_SIGNATURE):
        return "openpyxl"
    if data.startswith(OLE2_SIGNATURE):
        return "xlrd"
    raise ValueError("не похоже на файл Excel: неизвестная сигнатура")


def read_table(name: str, data: bytes) -> pd.DataFrame:
    """Прочитать первый лист книги как таблицу строк без заголовков.

    `dtype=str` обязателен: иначе ведущий ноль в GTIN пропадёт, а коды
    со спецсимволами превратятся в числа или даты.
    """
    try:
        engine = detect_engine(data)
    except ValueError as exc:
        raise ValueError(f"{name}: {exc}") from exc

    frame = pd.read_excel(
        BytesIO(data),
        engine=engine,
        sheet_name=0,
        header=None,
        dtype=str,
    )
    # Excel нередко оставляет в разметке листа пустые хвостовые строки.
    return frame.dropna(how="all").reset_index(drop=True)


def merge_tables(
    tables: list[tuple[str, pd.DataFrame]],
) -> tuple[pd.DataFrame, list[str]]:
    """Склеить таблицы вертикально, выровняв столбцы по позиции.

    Возвращает результат и список предупреждений о файлах, ширина которых
    отличается от остальных.
    """
    if not tables:
        return pd.DataFrame(), []

    width = max(frame.shape[1] for _, frame in tables)
    warnings: list[str] = []
    frames: list[pd.DataFrame] = []

    for name, frame in tables:
        if frame.shape[1] != width:
            warnings.append(
                f"{name}: колонок {frame.shape[1]} вместо {width} — "
                "недостающие заполнены пустыми значениями"
            )
        frames.append(frame.reindex(columns=range(width)))

    merged = pd.concat(frames, ignore_index=True)
    return merged.fillna(""), warnings


def collect_stats(
    tables: list[tuple[str, pd.DataFrame]], merged: pd.DataFrame
) -> dict:
    """Собрать статистику для показа в интерфейсе."""
    dup_count = 0
    if not merged.empty and CODE_COLUMN in merged.columns:
        dup_count = int(merged[CODE_COLUMN].duplicated().sum())

    return {
        "total_rows": len(merged),
        "columns": merged.shape[1],
        "per_file": [{"Файл": name, "Строк": len(frame)} for name, frame in tables],
        "dup_count": dup_count,
    }


def drop_duplicate_codes(frame: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """Убрать повторяющиеся коды, оставив первое вхождение."""
    cleaned = frame.drop_duplicates(subset=[CODE_COLUMN], keep="first").reset_index(
        drop=True
    )
    return cleaned, len(frame) - len(cleaned)


def to_xlsx_bytes(frame: pd.DataFrame) -> bytes:
    """Записать таблицу в xlsx без шапки и без индекса.

    Режим `write_only` не держит в памяти сетку ячеек — на 60 000+ строк это
    заметно быстрее `DataFrame.to_excel`. Значения уже строки, поэтому
    openpyxl запишет их текстом и ведущий ноль в GTIN сохранится.
    """
    workbook = Workbook(write_only=True)
    sheet = workbook.create_sheet()

    for row in frame.itertuples(index=False, name=None):
        sheet.append(list(row))

    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()
