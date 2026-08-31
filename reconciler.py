"""Сверка выданных кодов маркировки с отчётом об использовании."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from merger import CODE_COLUMN

#: Значащая часть кода GS1: "01" + GTIN (14 цифр) + "21" + серийный номер (13 символов).
#: В выгрузке заказа за ней идёт криптохвост (разделитель GS + "93" + подпись),
#: а в отчёте об использовании его нет — поэтому сравниваем только начало кода.
KEY_LENGTH = 31


@dataclass
class Reconciliation:
    """Результат сверки. `used` и `unused` — срезы исходной таблицы всех кодов."""

    used: pd.DataFrame
    unused: pd.DataFrame
    orphan_count: int
    duplicate_count: int


def code_keys(codes: pd.Series) -> pd.Series:
    """Привести коды к общему виду, отрезав криптохвост."""
    return codes.astype(str).str.slice(0, KEY_LENGTH)


def reconcile(all_codes: pd.DataFrame, used_codes: pd.DataFrame) -> Reconciliation:
    """Разделить все выданные коды на использованные и оставшиеся.

    Сравнение идёт через `isin` по множеству ключей, а не через `merge`: так
    строки не размножаются на дублях и в результат не попадают коды отчёта,
    которых нет в общем списке (их число возвращается в `orphan_count`).
    """
    empty = all_codes.iloc[0:0]
    if all_codes.empty:
        return Reconciliation(used=empty, unused=empty, orphan_count=0, duplicate_count=0)

    keys = code_keys(all_codes[CODE_COLUMN])
    used_keys: set[str] = set()
    if not used_codes.empty:
        used_keys = set(code_keys(used_codes[CODE_COLUMN]))

    is_used = keys.isin(used_keys)

    return Reconciliation(
        used=all_codes[is_used].reset_index(drop=True),
        unused=all_codes[~is_used].reset_index(drop=True),
        orphan_count=len(used_keys - set(keys)),
        duplicate_count=int(keys.duplicated().sum()),
    )
