"""Страница: сверка выданных кодов с отчётом об использовании."""

from __future__ import annotations

import streamlit as st

from reconciler import KEY_LENGTH, reconcile
from ui import download_xlsx, preview, spaced, upload_and_merge

st.title("Сверка использованных кодов")
st.caption(
    f"Коды сопоставляются по первым {KEY_LENGTH} символам, поэтому криптохвост "
    "в выгрузке заказа сравнению не мешает."
)

all_column, used_column = st.columns(2)

with all_column:
    st.subheader("Все коды")
    _, all_codes = upload_and_merge(
        "Файлы с выданными кодами",
        key="reconcile_all",
        help="Выгрузки заказа: код, GTIN, наименование.",
    )

with used_column:
    st.subheader("Использованные коды")
    _, used_codes = upload_and_merge(
        "Файлы с использованными кодами",
        key="reconcile_used",
        help="Отчёты об использовании: достаточно одной колонки с кодом.",
    )

if all_codes.empty or used_codes.empty:
    st.info(
        "Загрузите файлы обоих видов — после этого появятся три файла "
        "для скачивания: все коды, использованные и неиспользованные."
    )
    st.stop()

result = reconcile(all_codes, used_codes)

total = len(all_codes)
share = len(result.used) / total * 100 if total else 0

total_column, used_metric, unused_metric = st.columns(3)
total_column.metric("Всего кодов", spaced(total))
used_metric.metric("Использовано", spaced(len(result.used)), delta=f"{share:.1f}%")
unused_metric.metric("Не использовано", spaced(len(result.unused)))

if result.orphan_count:
    st.error(
        f"В отчёте об использовании {spaced(result.orphan_count)} кодов, которых нет "
        "среди выданных. Похоже, файлы относятся к разным заказам — эти коды "
        "в итоговые файлы не попадут."
    )

if result.duplicate_count:
    st.warning(
        f"Среди выданных кодов есть повторы: {spaced(result.duplicate_count)}. "
        "Проверьте, не загружена ли одна и та же выгрузка дважды."
    )

all_tab, used_tab, unused_tab = st.tabs(
    ["Все коды", "Использованные", "Неиспользованные"]
)
with all_tab:
    preview(all_codes)
with used_tab:
    preview(result.used)
with unused_tab:
    preview(result.unused)

st.subheader("Скачать результат")
first, second, third = st.columns(3)
with first:
    download_xlsx(
        "Все коды", all_codes, f"все_коды_{total}.xlsx", key="download_all"
    )
with second:
    download_xlsx(
        "Использованные",
        result.used,
        f"использованные_{len(result.used)}.xlsx",
        key="download_used",
    )
with third:
    download_xlsx(
        "Неиспользованные",
        result.unused,
        f"неиспользованные_{len(result.unused)}.xlsx",
        key="download_unused",
    )
