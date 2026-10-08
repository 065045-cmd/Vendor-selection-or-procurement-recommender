"""Loading and validating vendor data."""

from __future__ import annotations

from pathlib import Path
from typing import IO

import pandas as pd

from .criteria import CRITERIA

SAMPLE_DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "sample_vendors.csv"

TEXT_COLUMNS = ("vendor_name", "region")
NUMERIC_COLUMNS = tuple(c.key for c in CRITERIA)
REQUIRED_COLUMNS = TEXT_COLUMNS + NUMERIC_COLUMNS

QUALITY_MIN, QUALITY_MAX = 1.0, 5.0


def load_vendors(source: str | Path | IO = SAMPLE_DATA_PATH) -> pd.DataFrame:
    """Read vendor data from a CSV path or file-like object and validate it."""
    df = pd.read_csv(source)
    df.columns = [str(c).strip() for c in df.columns]
    return validate_vendors(df)


def validate_vendors(df: pd.DataFrame) -> pd.DataFrame:
    """Return a cleaned copy of ``df`` or raise ``ValueError`` describing the problem."""
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required column(s): {', '.join(missing)}")

    df = df[list(REQUIRED_COLUMNS)].copy()

    for col in TEXT_COLUMNS:
        df[col] = df[col].astype("string").str.strip().replace("", pd.NA)

    for col in NUMERIC_COLUMNS:
        converted = pd.to_numeric(df[col], errors="coerce")
        bad = converted.isna() & df[col].notna()
        if bad.any():
            rows = ", ".join(str(i + 2) for i in df.index[bad])  # +2: header row, 1-based
            raise ValueError(f"Column '{col}' has non-numeric values (CSV row(s) {rows})")
        df[col] = converted.astype(float)

    missing_cols = [c for c in REQUIRED_COLUMNS if df[c].isna().any()]
    if missing_cols:
        raise ValueError(f"Missing values in column(s): {', '.join(missing_cols)}")

    if len(df) < 2:
        raise ValueError("At least 2 vendors are needed to compare.")

    dupes = df.loc[df["vendor_name"].duplicated(), "vendor_name"].unique()
    if len(dupes):
        raise ValueError(f"Duplicate vendor name(s): {', '.join(dupes)}")

    if (df["unit_cost"] <= 0).any():
        raise ValueError("unit_cost must be greater than 0.")
    if (df["lead_time_days"] < 0).any():
        raise ValueError("lead_time_days cannot be negative.")
    if ((df["quality_rating"] < QUALITY_MIN) | (df["quality_rating"] > QUALITY_MAX)).any():
        raise ValueError(f"quality_rating must be between {QUALITY_MIN:g} and {QUALITY_MAX:g}.")

    return df.reset_index(drop=True)
