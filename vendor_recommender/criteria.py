"""Evaluation criteria and weight presets."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Criterion:
    """A single vendor evaluation criterion.

    Attributes:
        key: Column name in the vendor table.
        label: Human-readable name shown in the UI and rationale.
        higher_is_better: True if a larger raw value is preferable.
        fmt: Format string used to display a raw value.
        best_phrase: Rationale wording for the best value, e.g. "Lowest unit cost".
        worst_phrase: Rationale wording for the worst value, e.g. "Highest unit cost".
    """

    key: str
    label: str
    higher_is_better: bool
    fmt: str
    best_phrase: str
    worst_phrase: str

    def format(self, value: float) -> str:
        return self.fmt.format(value)


CRITERIA: tuple[Criterion, ...] = (
    Criterion(
        "unit_cost", "Cost", higher_is_better=False, fmt="${:,.2f}",
        best_phrase="Lowest unit cost", worst_phrase="Highest unit cost",
    ),
    Criterion(
        "quality_rating", "Quality", higher_is_better=True, fmt="{:.1f}/5",
        best_phrase="Highest quality rating", worst_phrase="Lowest quality rating",
    ),
    Criterion(
        "lead_time_days", "Lead time", higher_is_better=False, fmt="{:.0f} days",
        best_phrase="Shortest lead time", worst_phrase="Longest lead time",
    ),
)

CRITERIA_BY_KEY: dict[str, Criterion] = {c.key: c for c in CRITERIA}

# Raw slider values (0-100); they are normalized to sum to 1 before scoring.
PRESETS: dict[str, dict[str, float]] = {
    "Balanced": {"unit_cost": 34, "quality_rating": 33, "lead_time_days": 33},
    "Cost-focused": {"unit_cost": 60, "quality_rating": 25, "lead_time_days": 15},
    "Quality-focused": {"unit_cost": 20, "quality_rating": 60, "lead_time_days": 20},
    "Speed-focused": {"unit_cost": 20, "quality_rating": 20, "lead_time_days": 60},
}

DEFAULT_PRESET = "Balanced"
