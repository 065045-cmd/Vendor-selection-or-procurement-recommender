from tests.conftest import make_vendors
from vendor_recommender import PRESETS, build_rationale, score_vendors
from vendor_recommender.rationale import ordinal

EQUAL = {"unit_cost": 1, "quality_rating": 1, "lead_time_days": 1}


def rationale_for(df, name, weights=EQUAL):
    ranked = score_vendors(df, weights)
    row = ranked.index[ranked["vendor_name"] == name][0]
    return build_rationale(ranked, row, weights)


def test_ordinal():
    assert [ordinal(n) for n in (1, 2, 3, 4, 11, 12, 13, 21, 22, 101)] == [
        "1st", "2nd", "3rd", "4th", "11th", "12th", "13th", "21st", "22nd", "101st"
    ]


def test_best_and_worst_criteria_are_called_out():
    df = make_vendors([("Cheap", 10, 2, 30), ("Mid", 20, 3, 20), ("Premium", 30, 5, 10)])
    points = rationale_for(df, "Cheap")
    assert any("Lowest unit cost ($10.00 — best of 3)" in p for p in points)
    assert any("Lowest quality rating (2.0/5 — worst of 3)" in p for p in points)
    assert any("Longest lead time (30 days — worst of 3)" in p for p in points)
    # Strengths come before weaknesses.
    kinds = [p.split(":")[0] for p in points]
    assert kinds.index("**Strength") < kinds.index("**Weakness")


def test_tied_best_is_labelled():
    df = make_vendors([("A", 10, 4, 10), ("B", 10, 3, 20), ("C", 20, 5, 5)])
    points = rationale_for(df, "A")
    assert any("tied best of 3" in p and "unit cost" in p for p in points)


def test_criterion_with_no_spread_is_neutral():
    df = make_vendors([("A", 10, 4, 14), ("B", 20, 4, 7)])
    points = rationale_for(df, "A")
    assert any(p.startswith("**Neutral:** Quality is 4.0/5 for every vendor") for p in points)
    assert not any("quality rating" in p.lower() and "Strength" in p for p in points)


def test_main_driver_reflects_weights():
    df = make_vendors([("A", 10, 2, 30), ("B", 30, 5, 10)])
    points = rationale_for(df, "A", {"unit_cost": 60, "quality_rating": 20, "lead_time_days": 20})
    assert "**Main driver:** Cost accounts for 100% of this score (you weighted cost at 60%)." in points


def test_top_vendor_compared_with_runner_up():
    df = make_vendors([("Fast", 15, 4, 5), ("Slow", 12, 4, 30)])
    weights = {"unit_cost": 30, "quality_rating": 0, "lead_time_days": 70}
    points = rationale_for(df, "Fast", weights)
    assert points[-1] == (
        "**Why #1:** Leads #2 Slow by 40.0 pts, mainly on lead time (+70.0) "
        "despite trailing on cost (−30.0)."
    )


def test_lower_vendor_compared_with_vendor_above():
    df = make_vendors([("Fast", 15, 4, 5), ("Slow", 12, 4, 30)])
    weights = {"unit_cost": 30, "quality_rating": 0, "lead_time_days": 70}
    points = rationale_for(df, "Slow", weights)
    assert points[-1] == (
        "**Gap:** Trails #1 Fast by 40.0 pts, chiefly on lead time (−70.0), "
        "though it beats them on cost (+30.0)."
    )


def test_tie_on_total_is_explained():
    df = make_vendors([("B", 20, 5, 10), ("C", 10, 1, 10)])
    weights = {"unit_cost": 1, "quality_rating": 1}
    assert rationale_for(df, "C", weights)[-1].startswith("**Why #1:** Ties #2 B on total score")
    assert rationale_for(df, "B", weights)[-1].startswith("**Gap:** Ties #1 C on total score")


def test_single_vendor():
    df = make_vendors([("Only", 10, 4, 5)])
    ranked = score_vendors(df, EQUAL)
    points = build_rationale(ranked, 0, EQUAL)
    assert points[-1] == "**Note:** This is the only vendor that meets your constraints."


def test_every_sample_vendor_gets_a_rationale(sample_vendors):
    ranked = score_vendors(sample_vendors, PRESETS["Balanced"])
    for row in range(len(ranked)):
        points = build_rationale(ranked, row, PRESETS["Balanced"])
        assert any(p.startswith("**Main driver:**") or p.startswith("**Note:**") for p in points)
        assert points[-1].startswith("**Why #1:**" if row == 0 else "**Gap:**")
