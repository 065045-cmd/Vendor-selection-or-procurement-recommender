"""Weighted-sum vendor scoring.

Each criterion is min-max normalized to a 0-100 score across the vendors being
compared (inverted for criteria where lower is better), multiplied by its
normalized weight, and summed into a 0-100 total score.
"""

from __future__ import annotations

from collections.abc import Mapping

import pandas as pd

from .criteria import CRITERIA


def score_col(key: str) -> str:
    return f"score_{key}"


def contrib_col(key: str) -> str:
    return f"contrib_{key}"


def normalize_weights(raw: Mapping[str, float]) -> dict[str, float]:
    """Scale raw weights so they sum to 1.

    Criteria missing from ``raw`` get weight 0. If every weight is 0 the
    criteria are weighted equally.
    """
    values = {c.key: float(raw.get(c.key, 0.0)) for c in CRITERIA}
    if any(v < 0 for v in values.values()):
        raise ValueError("Weights cannot be negative.")
    total = sum(values.values())
    if total == 0:
        return {k: 1 / len(values) for k in values}
    return {k: v / total for k, v in values.items()}


def normalize(values: pd.Series, higher_is_better: bool) -> pd.Series:
    """Min-max normalize to 0-100, where 100 is always the most preferable value.

    If every vendor has the same value the criterion cannot separate them, so
    all get 100.
    """
    lo, hi = values.min(), values.max()
    if hi == lo:
        return pd.Series(100.0, index=values.index)
    scaled = (values - lo) / (hi - lo) if higher_is_better else (hi - values) / (hi - lo)
    return scaled * 100.0


def score_vendors(vendors: pd.DataFrame, weights: Mapping[str, float]) -> pd.DataFrame:
    """Score and rank vendors.

    Returns a copy of ``vendors`` sorted best-first with, for each criterion,
    ``score_<key>`` (0-100) and ``contrib_<key>`` (weight x score), plus
    ``total_score`` (0-100) and ``rank`` (1 = best). Ties on total score are
    broken by lower unit cost, then vendor name.
    """
    w = normalize_weights(weights)
    df = vendors.copy()
    for c in CRITERIA:
        df[score_col(c.key)] = normalize(df[c.key], c.higher_is_better)
        df[contrib_col(c.key)] = df[score_col(c.key)] * w[c.key]
    df["total_score"] = sum(df[contrib_col(c.key)] for c in CRITERIA)

    # Round the sort key so floating-point noise doesn't decide ties.
    df["_sort_total"] = df["total_score"].round(9)
    df = df.sort_values(
        ["_sort_total", "unit_cost", "vendor_name"], ascending=[False, True, True]
    ).drop(columns="_sort_total")
    df = df.reset_index(drop=True)
    df["rank"] = range(1, len(df) + 1)
    return df


def apply_constraints(
    vendors: pd.DataFrame,
    max_unit_cost: float | None = None,
    min_quality: float | None = None,
    max_lead_time: float | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Split vendors into those meeting the hard constraints and those that don't.

    Returns ``(eligible, excluded)``; ``excluded`` has columns ``vendor_name``
    and ``reason``. A constraint of ``None`` is not applied.
    """
    checks = []
    if max_unit_cost is not None:
        checks.append(
            (vendors["unit_cost"] > max_unit_cost, f"unit cost above ${max_unit_cost:,.2f}")
        )
    if min_quality is not None:
        checks.append(
            (vendors["quality_rating"] < min_quality, f"quality below {min_quality:.1f}/5")
        )
    if max_lead_time is not None:
        checks.append(
            (vendors["lead_time_days"] > max_lead_time, f"lead time over {max_lead_time:.0f} days")
        )

    reasons = pd.Series([[] for _ in range(len(vendors))], index=vendors.index, dtype=object)
    for failed, reason in checks:
        for idx in vendors.index[failed]:
            reasons[idx].append(reason)

    is_excluded = reasons.map(bool)
    eligible = vendors[~is_excluded].reset_index(drop=True)
    excluded = pd.DataFrame(
        {
            "vendor_name": vendors.loc[is_excluded, "vendor_name"],
            "reason": reasons[is_excluded].map("; ".join),
        }
    ).reset_index(drop=True)
    return eligible, excluded
