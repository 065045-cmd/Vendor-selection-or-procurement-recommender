"""Vendor selection / procurement recommender."""

from .criteria import CRITERIA, DEFAULT_PRESET, PRESETS, Criterion
from .data import SAMPLE_DATA_PATH, load_vendors, validate_vendors
from .rationale import build_rationale
from .scoring import apply_constraints, normalize, normalize_weights, score_vendors

__all__ = [
    "CRITERIA",
    "DEFAULT_PRESET",
    "PRESETS",
    "SAMPLE_DATA_PATH",
    "Criterion",
    "apply_constraints",
    "build_rationale",
    "load_vendors",
    "normalize",
    "normalize_weights",
    "score_vendors",
    "validate_vendors",
]
