"""Общие элементы интерфейса для страниц приложения."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from merger import merge_tables, read_table, to_xlsx_bytes

PREVIEW_ROWS = 50
XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@st.cache_data(show_spinner=False)
def load_table(name: str, data: bytes) -> pd.DataFrame:
    """Разбор файла с кэшем по его байтам: десятки тысяч строк не перечитываются на каждый клик."""
    return read_table(name, data)


@st.cache_data(show_spinner=False)
def build_xlsx(frame: pd.DataFrame) -> bytes:
    return to_xlsx_bytes(frame)


def spaced(number: int) -> str:
    return f"{number:,}".replace(",", " ")


def upload_and_merge(
    label: str, key: str, help: str | None = None
) -> tuple[list[tuple[str, pd.DataFrame]], pd.DataFrame]:
    """Загрузчик нескольких файлов, их разбор и склейка по позиции столбцов.

    Ошибки чтения и расхождения по числу колонок показывает сама. Аргумент `key`
    обязателен: на странице сверки два таких загрузчика на одном экране.
    """
    uploaded = st.file_uploader(
        label,
        type=["xlsx", "xls"],
        accept_multiple_files=True,
        key=key,
        help=help,
    )

    tables: list[tuple[str, pd.DataFrame]] = []
    for item in uploaded or []:
        try:
            tables.append((item.name, load_table(item.name, item.getvalue())))
        except Exception as exc:  # noqa: BLE001 — показываем пользователю любую ошибку разбора
            st.error(f"Не удалось прочитать «{item.name}»: {exc}")

    if not tables:
        return [], pd.DataFrame()

    merged, warnings = merge_tables(tables)
    for message in warnings:
        st.warning(message)

    return tables, merged


def preview(frame: pd.DataFrame) -> None:
    st.caption(f"Первые {PREVIEW_ROWS} строк из {spaced(len(frame))}")
    st.dataframe(frame.head(PREVIEW_ROWS), use_container_width=True)


def download_xlsx(label: str, frame: pd.DataFrame, file_name: str, key: str) -> None:
    st.download_button(
        label,
        data=build_xlsx(frame),
        file_name=file_name,
        mime=XLSX_MIME,
        key=key,
        use_container_width=True,
    )
