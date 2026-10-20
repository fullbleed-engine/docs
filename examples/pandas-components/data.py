# SPDX-License-Identifier: MIT
"""The example's CSV contract; pandas is an optional application dependency."""
from decimal import Decimal
from pathlib import Path

import pandas as pd

COLUMNS = ("sku", "product", "category", "units", "net_sales_cents", "last_restock")


def load_products(path: str | Path) -> pd.DataFrame:
    frame = pd.read_csv(path, dtype={
        "sku": "string", "product": "string", "category": "string",
        "units": "Int64", "net_sales_cents": "Int64", "last_restock": "string",
    })
    missing = set(COLUMNS) - set(frame.columns)
    if missing:
        raise ValueError(f"Missing columns: {', '.join(sorted(missing))}")
    frame = frame.loc[:, list(COLUMNS)].copy()
    if frame.empty:
        raise ValueError("The CSV must contain at least one product")
    if frame[list(COLUMNS[:-1])].isna().any().any():
        raise ValueError("Only last_restock may be missing")
    for column in ("sku", "product", "category"):
        frame[column] = frame[column].str.strip()
        if frame[column].eq("").any():
            raise ValueError(f"{column} must not be blank")
    if frame["sku"].duplicated().any():
        raise ValueError("Each SKU must be unique")
    if frame["units"].lt(0).any():
        raise ValueError("units must be nonnegative")
    frame["last_restock"] = pd.to_datetime(frame["last_restock"], format="%Y-%m-%d", errors="raise")
    return frame


def dollars(cents: int) -> str:
    amount = Decimal(int(cents)) / 100
    return f"-${abs(amount):,.2f}" if amount < 0 else f"${amount:,.2f}"


def restock(value) -> str:
    return "Not recorded" if pd.isna(value) else value.strftime("%d %b %Y")


def totals(frame: pd.DataFrame) -> dict:
    # Python ints avoid silent int64 overflow when summing pandas columns.
    return {"products": len(frame), "units": sum(map(int, frame["units"])),
            "cents": sum(map(int, frame["net_sales_cents"])),
            "categories": frame["category"].nunique()}
