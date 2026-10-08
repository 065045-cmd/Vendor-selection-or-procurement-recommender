"""Plain-language rationale for a vendor's position in the ranking."""

from __future__ import annotations

from collections.abc import Mapping

import pandas as pd

from .criteria import CRITERIA, CRITERIA_BY_KEY, Criterion
from .scoring import contrib_col, normalize_weights, score_col

STRONG_SCORE = 70.0
WEAK_SCORE = 30.0
# Score differences smaller than this (in points) are treated as ties.
TIE_EPSILON = 0.05


def ordinal(n: int) -> str:
    if 10 <= n % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def _criterion_position(ranked: pd.DataFrame, c: Criterion, row: int) -> int:
    """1-based position of ``row`` on criterion ``c`` (ties share the better position)."""
    positions = ranked[c.key].rank(ascending=not c.higher_is_better, method="min")
    return int(positions.iloc[row])


def _criterion_points(ranked: pd.DataFrame, row: int) -> list[str]:
    """Strengths, then weaknesses, then criteria that don't separate vendors."""
    n = len(ranked)
    vendor = ranked.iloc[row]
    strengths, weaknesses, neutral = [], [], []
    for c in CRITERIA:
        value = c.format(vendor[c.key])
        if ranked[c.key].nunique() == 1:
            neutral.append(
                f"**Neutral:** {c.label} is {value} for every vendor, so it doesn't separate them."
            )
            continue

        pos = _criterion_position(ranked, c, row)
        score = vendor[score_col(c.key)]
        if pos == 1:
            shared = (ranked[c.key] == vendor[c.key]).sum() > 1
            best = "tied best" if shared else "best"
            strengths.append(f"**Strength:** {c.best_phrase} ({value} — {best} of {n}).")
        elif score >= STRONG_SCORE:
            strengths.append(f"**Strength:** {c.label} of {value} ranks {ordinal(pos)} of {n}.")
        elif score == 0:
            weaknesses.append(f"**Weakness:** {c.worst_phrase} ({value} — worst of {n}).")
        elif score <= WEAK_SCORE:
            weaknesses.append(f"**Weakness:** {c.label} of {value} ranks {ordinal(pos)} of {n}.")
    return strengths + weaknesses + neutral


def _driver_point(vendor: pd.Series, weights: Mapping[str, float]) -> str:
    total = vendor["total_score"]
    if total <= TIE_EPSILON:
        return "**Note:** Scores lowest on every weighted criterion."
    main = max(CRITERIA, key=lambda c: vendor[contrib_col(c.key)])
    share = vendor[contrib_col(main.key)] / total
    return (
        f"**Main driver:** {main.label} accounts for {share:.0%} of this score "
        f"(you weighted {main.label.lower()} at {weights[main.key]:.0%})."
    )


def _contribution_deltas(a: pd.Series, b: pd.Series) -> list[tuple[str, float]]:
    """Per-criterion weighted-point difference ``a - b``, largest first."""
    deltas = [(c.key, a[contrib_col(c.key)] - b[contrib_col(c.key)]) for c in CRITERIA]
    return sorted(deltas, key=lambda kv: kv[1], reverse=True)


def _comparison_point(ranked: pd.DataFrame, row: int) -> str:
    if len(ranked) == 1:
        return "**Note:** This is the only vendor that meets your constraints."

    vendor = ranked.iloc[row]
    if row == 0:
        other = ranked.iloc[1]
        margin = vendor["total_score"] - other["total_score"]
        if margin < TIE_EPSILON:
            return (
                f"**Why #1:** Ties #2 {other['vendor_name']} on total score; "
                "placed first on the tie-break (lower unit cost, then name)."
            )
        deltas = _contribution_deltas(vendor, other)
        gain_key, gain = deltas[0]
        text = (
            f"**Why #1:** Leads #2 {other['vendor_name']} by {margin:.1f} pts, "
            f"mainly on {CRITERIA_BY_KEY[gain_key].label.lower()} (+{gain:.1f})"
        )
        loss_key, loss = deltas[-1]
        if loss <= -TIE_EPSILON:
            text += f" despite trailing on {CRITERIA_BY_KEY[loss_key].label.lower()} (−{-loss:.1f})"
        return text + "."

    above = ranked.iloc[row - 1]
    margin = above["total_score"] - vendor["total_score"]
    if margin < TIE_EPSILON:
        return (
            f"**Gap:** Ties #{row} {above['vendor_name']} on total score; "
            "placed lower on the tie-break (lower unit cost, then name)."
        )
    deltas = _contribution_deltas(vendor, above)
    loss_key, loss = deltas[-1]
    text = (
        f"**Gap:** Trails #{row} {above['vendor_name']} by {margin:.1f} pts, "
        f"chiefly on {CRITERIA_BY_KEY[loss_key].label.lower()} (−{-loss:.1f})"
    )
    gain_key, gain = deltas[0]
    if gain >= TIE_EPSILON:
        text += f", though it beats them on {CRITERIA_BY_KEY[gain_key].label.lower()} (+{gain:.1f})"
    return text + "."


def build_rationale(ranked: pd.DataFrame, row: int, weights: Mapping[str, float]) -> list[str]:
    """Explain why the vendor at position ``row`` of ``ranked`` sits where it does.

    ``ranked`` is the output of :func:`score_vendors`; ``weights`` are the raw
    or normalized weights used to score it. Returns Markdown bullet texts.
    """
    w = normalize_weights(weights)
    vendor = ranked.iloc[row]
    points = _criterion_points(ranked, row)
    points.append(_driver_point(vendor, w))
    points.append(_comparison_point(ranked, row))
    return points
