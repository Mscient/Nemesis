"""
Series preparation — D2.

Converts a list of SalesRecord into a contiguous daily pandas DataFrame,
filling gaps, deduplicating, and preserving optional columns.
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Sequence

import pandas as pd

from stocksense_core.types import SalesRecord


# ---------------------------------------------------------------------------
# Public helper
# ---------------------------------------------------------------------------

def build_daily_series(records: Sequence[SalesRecord]) -> pd.DataFrame:
    """
    Build a contiguous daily DataFrame from SalesRecord objects.

    Columns produced:
        date         — datetime64[ns]
        units_sold   — float  (gaps filled with NaN then 0)
        on_hand      — float  (optional; gaps forward-filled)
        promo_flag   — int    (optional; gaps filled with 0)
        duplicate    — bool   flag for dates that appeared more than once
                               (only the first occurrence is kept)

    The returned DataFrame is sorted by date, with no missing calendar days
    between the first and last record.
    """
    if not records:
        return pd.DataFrame(columns=["date", "units_sold", "on_hand", "promo_flag", "duplicate"])

    df = pd.DataFrame(
        [
            {
                "date": pd.Timestamp(r.date),
                "units_sold": r.units_sold,
                "on_hand": r.on_hand,
                "promo_flag": r.promo_flag if r.promo_flag is not None else 0,
            }
            for r in records
        ]
    )

    # Detect duplicate dates before deduplication
    df["duplicate"] = df["date"].duplicated(keep=False)

    # Keep first occurrence of each date
    df = df.drop_duplicates(subset="date", keep="first").sort_values("date").reset_index(drop=True)

    # Build a complete date range and reindex to fill gaps
    full_range = pd.date_range(df["date"].min(), df["date"].max(), freq="D")
    df = df.set_index("date").reindex(full_range)
    df.index.name = "date"
    df = df.reset_index()

    # Fill missing values sensibly
    df["units_sold"] = df["units_sold"].fillna(0.0)
    df["on_hand"] = df["on_hand"].ffill()          # carry forward inventory levels
    df["promo_flag"] = df["promo_flag"].fillna(0).astype(int)
    df["duplicate"] = df["duplicate"].fillna(False)

    return df


def to_sales_records(df: pd.DataFrame, sku: str) -> list[SalesRecord]:
    """Convert a daily DataFrame back to a list of SalesRecord (used internally)."""
    out: list[SalesRecord] = []
    for row in df.itertuples(index=False):
        out.append(
            SalesRecord(
                date=row.date.date() if hasattr(row.date, "date") else row.date,
                sku=sku,
                units_sold=float(row.units_sold),
                on_hand=float(row.on_hand) if pd.notna(row.on_hand) else None,
                promo_flag=int(row.promo_flag) if pd.notna(row.promo_flag) else None,
            )
        )
    return out
