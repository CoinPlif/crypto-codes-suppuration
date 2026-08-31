"""Страница: объединение нескольких Excel-файлов в один."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from merger import collect_stats, drop_duplicate_codes
from ui import download_xlsx, preview, spaced, upload_and_merge

st.title("Объединение Excel-файлов с кодами маркировки")

tables, merged = upload_and_merge(
    "Excel-файлы для объединения",
    key="merge_files",
    help="Шапка не ожидается: первая строка файла считается данными.",
)

if not tables:
    st.info(
        "Загрузите два или больше файла — они склеятся по порядку, "
        "столбец под соответствующий столбец."
    )
    st.stop()

stats = collect_stats(tables, merged)

removed = 0
if stats["dup_count"]:
    st.warning(f"Найдено повторяющихся кодов: {spaced(stats['dup_count'])}")
    if st.checkbox("Удалить дубликаты кодов (оставить первое вхождение)"):
        merged, removed = drop_duplicate_codes(merged)

rows_column, columns_column, files_column = st.columns(3)
rows_column.metric("Строк в итоговом файле", spaced(len(merged)))
columns_column.metric("Колонок", merged.shape[1])
files_column.metric("Файлов", len(tables))

if removed:
    st.success(f"Удалено дубликатов: {spaced(removed)}")

st.subheader("Строк по файлам")
st.dataframe(
    pd.DataFrame(stats["per_file"]), hide_index=True, use_container_width=True
)

st.subheader("Результат")
preview(merged)

default_name = f"merged_{len(tables)}_files_{len(merged)}_rows.xlsx"
filename = st.text_input("Имя итогового файла", value=default_name)
download_xlsx(
    "Скачать объединённый файл",
    merged,
    filename or default_name,
    key="download_merged",
)
