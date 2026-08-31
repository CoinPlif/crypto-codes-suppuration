"""Тесты сверки выданных кодов с отчётом об использовании."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from merger import read_table, to_xlsx_bytes  # noqa: E402 — путь к пакету добавляется выше
from reconciler import reconcile  # noqa: E402

GTIN = "04688749270197"
PRODUCT = "РБКУ SS Фо Хо лапша рисовая (пакет 200г) 24"

#: Ключ длиной 31 символ — то, что видно в отчёте об использовании.
KEY = "0104688749270197215jghiQtiKTn<S"
#: Тот же код в выгрузке заказа: криптохвост после разделителя GS.
KEY_WITH_CRYPTO = KEY + "_x001D_93ApdZ"


def all_codes(*codes: str) -> pd.DataFrame:
    return pd.DataFrame([[code, GTIN, PRODUCT] for code in codes])


def used_codes(*codes: str) -> pd.DataFrame:
    return pd.DataFrame([[code] for code in codes])


def test_crypto_tail_is_ignored_when_matching():
    """Главный тест: 44-символьный код заказа должен найтись по 31-символьному ключу."""
    result = reconcile(all_codes(KEY_WITH_CRYPTO), used_codes(KEY))

    assert len(result.used) == 1
    assert result.unused.empty
    assert result.used.iloc[0, 0] == KEY_WITH_CRYPTO


def test_split_keeps_all_three_columns():
    result = reconcile(
        all_codes("code-1", "code-2", "code-3", "code-4", "code-5"),
        used_codes("code-2", "code-4"),
    )

    assert result.used[0].tolist() == ["code-2", "code-4"]
    assert result.unused[0].tolist() == ["code-1", "code-3", "code-5"]
    assert result.used.shape[1] == 3
    assert result.unused.shape[1] == 3


def test_used_and_unused_add_up_to_total():
    result = reconcile(all_codes(*[f"code-{i}" for i in range(10)]), used_codes("code-3"))

    assert len(result.used) + len(result.unused) == 10


def test_orphan_codes_are_counted_not_included():
    result = reconcile(all_codes("code-1"), used_codes("code-1", "чужой-код"))

    assert result.orphan_count == 1
    assert len(result.used) == 1
    assert result.unused.empty


def test_duplicates_among_issued_codes_are_counted():
    result = reconcile(all_codes("code-1", "code-1", "code-2"), used_codes("code-1"))

    assert result.duplicate_count == 1
    # Обе одинаковые строки попадают в использованные — строки не теряются и не множатся.
    assert len(result.used) == 2
    assert len(result.unused) == 1


def test_three_column_report_works_as_used_codes():
    """Если в поле «использованные» загрузили полный трёхколоночный файл — берётся колонка 0."""
    result = reconcile(all_codes("code-1", "code-2"), all_codes("code-2"))

    assert result.used[0].tolist() == ["code-2"]
    assert result.orphan_count == 0


def test_empty_report_leaves_everything_unused():
    result = reconcile(all_codes("code-1", "code-2"), pd.DataFrame())

    assert result.used.empty
    assert len(result.unused) == 2


def test_results_survive_xlsx_roundtrip():
    result = reconcile(all_codes(KEY_WITH_CRYPTO, "code-2"), used_codes(KEY))

    restored = read_table("used.xlsx", to_xlsx_bytes(result.used))

    assert len(restored) == 1
    assert restored[1].iloc[0] == GTIN
    assert restored[2].iloc[0] == PRODUCT
