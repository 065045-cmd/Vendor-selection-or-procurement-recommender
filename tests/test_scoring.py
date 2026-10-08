import pandas as pd
import pytest

from tests.conftest import make_vendors
from vendor_recommender import (
    PRESETS,
    apply_constraints,
    normalize,
    normalize_weights,
    score_vendors,
)


class TestNormalizeWeights:
    def test_scales_to_sum_to_one(self):
        w = normalize_weights({"unit_cost": 50, "quality_rating": 30, "lead_time_days": 20})
        assert w == pytest.approx({"unit_cost": 0.5, "quality_rating": 0.3, "lead_time_days": 0.2})

    def test_missing_criteria_get_zero(self):
        w = normalize_weights({"unit_cost": 10})
        assert w == {"unit_cost": 1.0, "quality_rating": 0.0, "lead_time_days": 0.0}

    def test_all_zero_falls_back_to_equal(self):
        w = normalize_weights({"unit_cost": 0, "quality_rating": 0, "lead_time_days": 0})
        assert w == pytest.approx({k: 1 / 3 for k in w})

    def test_negative_weight_rejected(self):
        with pytest.raises(ValueError, match="negative"):
            normalize_weights({"unit_cost": -1, "quality_rating": 1})


class TestNormalize:
    def test_higher_is_better(self):
        s = normalize(pd.Series([1.0, 3.0, 5.0]), higher_is_better=True)
        assert list(s) == [0.0, 50.0, 100.0]

    def test_lower_is_better_is_inverted(self):
        s = normalize(pd.Series([10.0, 15.0, 20.0]), higher_is_better=False)
        assert list(s) == [100.0, 50.0, 0.0]

    def test_zero_range_gives_everyone_full_marks(self):
        s = normalize(pd.Series([7.0, 7.0, 7.0]), higher_is_better=False)
        assert list(s) == [100.0, 100.0, 100.0]


class TestScoreVendors:
    def test_single_criterion_ranks_by_that_criterion(self):
        df = make_vendors([("A", 20, 3, 10), ("B", 10, 3, 10), ("C", 15, 3, 10)])
        ranked = score_vendors(df, {"unit_cost": 1})
        assert list(ranked["vendor_name"]) == ["B", "C", "A"]
        assert list(ranked["total_score"]) == [100.0, 50.0, 0.0]
        assert list(ranked["rank"]) == [1, 2, 3]

    def test_contributions_sum_to_total(self, sample_vendors):
        ranked = score_vendors(sample_vendors, PRESETS["Balanced"])
        contribs = ranked[[c for c in ranked.columns if c.startswith("contrib_")]].sum(axis=1)
        assert contribs.to_numpy() == pytest.approx(ranked["total_score"].to_numpy())
        assert ranked["total_score"].between(0, 100).all()

    def test_changing_weights_changes_winner(self):
        df = make_vendors([("Cheap", 10, 2, 30), ("Premium", 30, 5, 30)])
        assert score_vendors(df, {"unit_cost": 1})["vendor_name"].iloc[0] == "Cheap"
        assert score_vendors(df, {"quality_rating": 1})["vendor_name"].iloc[0] == "Premium"

    def test_ties_broken_by_cost_then_name(self):
        # Identical vendors: name decides.
        df = make_vendors([("Zeta", 10, 5, 10), ("Alpha", 10, 5, 10), ("Mid", 20, 3, 10)])
        ranked = score_vendors(df, {"unit_cost": 1, "quality_rating": 1})
        assert list(ranked["vendor_name"][:2]) == ["Alpha", "Zeta"]

        # Equal totals: B and C trade cost against quality symmetrically.
        df = make_vendors([("B", 20, 5, 10), ("C", 10, 1, 10)])
        ranked = score_vendors(df, {"unit_cost": 1, "quality_rating": 1})
        assert ranked["total_score"].iloc[0] == pytest.approx(ranked["total_score"].iloc[1])
        assert ranked["vendor_name"].iloc[0] == "C"  # cheaper wins the tie

    def test_does_not_mutate_input(self, sample_vendors):
        before = sample_vendors.copy()
        score_vendors(sample_vendors, PRESETS["Balanced"])
        pd.testing.assert_frame_equal(sample_vendors, before)

    def test_presets_pick_different_winners(self, sample_vendors):
        winners = {
            name: score_vendors(sample_vendors, w)["vendor_name"].iloc[0]
            for name, w in PRESETS.items()
            if name != "Balanced"
        }
        assert len(set(winners.values())) == len(winners), winners


class TestApplyConstraints:
    def test_no_constraints_keeps_everyone(self, sample_vendors):
        eligible, excluded = apply_constraints(sample_vendors)
        assert len(eligible) == len(sample_vendors)
        assert excluded.empty

    def test_excludes_with_reasons(self):
        df = make_vendors([("Ok", 10, 4, 5), ("Pricey", 50, 4, 5), ("Bad", 60, 2, 40)])
        eligible, excluded = apply_constraints(
            df, max_unit_cost=20, min_quality=3, max_lead_time=30
        )
        assert list(eligible["vendor_name"]) == ["Ok"]
        reasons = dict(zip(excluded["vendor_name"], excluded["reason"]))
        assert reasons["Pricey"] == "unit cost above $20.00"
        assert reasons["Bad"] == (
            "unit cost above $20.00; quality below 3.0/5; lead time over 30 days"
        )

    def test_bounds_are_inclusive(self):
        df = make_vendors([("Edge", 20, 3, 30), ("Other", 10, 4, 5)])
        eligible, _ = apply_constraints(df, max_unit_cost=20, min_quality=3, max_lead_time=30)
        assert "Edge" in set(eligible["vendor_name"])
