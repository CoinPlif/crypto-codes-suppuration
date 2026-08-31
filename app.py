"""Точка входа: навигация по страницам приложения.

Страницы лежат в `views/`, а не в `pages/`: при использовании `st.navigation`
каталог `pages/` включил бы вторую, автоматическую навигацию.
"""

from __future__ import annotations

import streamlit as st

st.set_page_config(page_title="Коды маркировки", layout="wide")

st.navigation(
    [
        st.Page(
            "views/merge_files.py",
            title="Объединение файлов",
            icon=":material/merge:",
            default=True,
        ),
        st.Page(
            "views/reconcile_codes.py",
            title="Сверка использованных",
            icon=":material/fact_check:",
        ),
    ]
).run()
