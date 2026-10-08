"""Streamlit UI for the vendor selection / procurement recommender.

Run with:  streamlit run app.py
"""

from __future__ import annotations

import altair as alt
import pandas as pd
import streamlit as st

from vendor_recommender import (
    CRITERIA,
    DEFAULT_PRESET,
    PRESETS,
    SAMPLE_DATA_PATH,
    apply_constraints,
    build_rationale,
    load_vendors,
    normalize_weights,
    score_vendors,
)
from vendor_recommender.scoring import contrib_col, score_col

CUSTOM_PRESET = "Custom"
DEFAULT_SHORTLIST_SIZE = 5
# Categorical slots 1-3 of the validated default chart palette, one per criterion.
CRITERION_COLORS = {
    "unit_cost": "#2a78d6",
    "quality_rating": "#eb6834",
    "lead_time_days": "#1baf7a",
}


def weight_key(criterion_key: str) -> str:
    return f"weight_{criterion_key}"


@st.cache_data
def get_vendors() -> pd.DataFrame:
    return load_vendors(SAMPLE_DATA_PATH)


def apply_preset() -> None:
    preset = PRESETS.get(st.session_state.preset)
    if preset is None:  # "Custom" keeps the current slider values
        return
    for key, value in preset.items():
        st.session_state[weight_key(key)] = value


def mark_custom() -> None:
    st.session_state.preset = CUSTOM_PRESET


def init_state() -> None:
    if "preset" not in st.session_state:
        st.session_state.preset = DEFAULT_PRESET
        apply_preset()


def sidebar(vendor_count: int) -> tuple[dict[str, float], int, dict[str, float | None]]:
    with st.sidebar:
        st.header("Criteria weights")
        st.selectbox(
            "Preset",
            options=[*PRESETS, CUSTOM_PRESET],
            key="preset",
            on_change=apply_preset,
            help="Start from a preset, then fine-tune with the sliders.",
        )
        raw_weights = {}
        for c in CRITERIA:
            direction = "higher is better" if c.higher_is_better else "lower is better"
            raw_weights[c.key] = st.slider(
                f"{c.label} ({direction})",
                min_value=0,
                max_value=100,
                step=1,
                key=weight_key(c.key),
                on_change=mark_custom,
            )
        weights = normalize_weights(raw_weights)
        if sum(raw_weights.values()) == 0:
            st.warning("All weights are zero, so every criterion is weighted equally.")
        st.caption(
            "Effective weights: "
            + " · ".join(f"{c.label} **{weights[c.key]:.0%}**" for c in CRITERIA)
        )

        st.header("Shortlist")
        shortlist_size = st.slider(
            "Vendors to shortlist",
            min_value=1,
            max_value=vendor_count,
            value=min(DEFAULT_SHORTLIST_SIZE, vendor_count),
        )

        with st.expander("Constraints (optional)"):
            st.caption("Vendors that fail a constraint are excluded before scoring.")
            constraints = {
                "max_unit_cost": st.number_input(
                    "Max unit cost ($)", min_value=0.0, value=None, step=0.5,
                    placeholder="No limit",
                ),
                "min_quality": st.number_input(
                    "Min quality rating (1–5)", min_value=1.0, max_value=5.0, value=None,
                    step=0.1, placeholder="No minimum",
                ),
                "max_lead_time": st.number_input(
                    "Max lead time (days)", min_value=0, value=None, step=1,
                    placeholder="No limit",
                ),
            }
    return weights, shortlist_size, constraints


def render_shortlist(ranked: pd.DataFrame, shortlist_size: int, weights: dict[str, float]) -> None:
    st.subheader(f"Ranked shortlist — top {min(shortlist_size, len(ranked))}")
    for row in range(min(shortlist_size, len(ranked))):
        vendor = ranked.iloc[row]
        with st.container(border=True):
            title_col, metric_col = st.columns([4, 1])
            title_col.markdown(f"#### #{vendor['rank']} · {vendor['vendor_name']}")
            title_col.caption(
                f"{vendor['region']} · "
                + " · ".join(f"{c.label}: {c.format(vendor[c.key])}" for c in CRITERIA)
            )
            metric_col.metric("Score", f"{vendor['total_score']:.1f}")
            st.progress(min(max(vendor["total_score"] / 100, 0.0), 1.0))
            st.markdown("\n".join(f"- {p}" for p in build_rationale(ranked, row, weights)))


def render_breakdown_chart(ranked: pd.DataFrame, shortlist_size: int) -> None:
    st.subheader("Score breakdown")
    st.caption(
        "Each bar is a vendor's total score (0–100), split into the weighted points it earns "
        "on each criterion. Faded bars are outside the shortlist."
    )
    rows = []
    for _, vendor in ranked.iterrows():
        for order, c in enumerate(CRITERIA):
            rows.append(
                {
                    "Vendor": vendor["vendor_name"],
                    "Rank": int(vendor["rank"]),
                    "Criterion": c.label,
                    "Value": c.format(vendor[c.key]),
                    "Criterion score": round(vendor[score_col(c.key)], 1),
                    "Weighted points": round(vendor[contrib_col(c.key)], 1),
                    "Total score": round(vendor["total_score"], 1),
                    "Shortlisted": vendor["rank"] <= shortlist_size,
                    "order": order,
                }
            )
    long = pd.DataFrame(rows)

    chart = (
        alt.Chart(long)
        .mark_bar(size=20)
        .encode(
            y=alt.Y(
                "Vendor:N",
                sort=list(ranked["vendor_name"]),
                title=None,
                axis=alt.Axis(labelLimit=240),
            ),
            x=alt.X(
                "Weighted points:Q",
                stack="zero",
                scale=alt.Scale(domain=[0, 100]),
                title="Total score",
            ),
            color=alt.Color(
                "Criterion:N",
                scale=alt.Scale(
                    domain=[c.label for c in CRITERIA],
                    range=[CRITERION_COLORS[c.key] for c in CRITERIA],
                ),
                legend=alt.Legend(orient="top", title=None),
            ),
            order=alt.Order("order:Q"),
            opacity=alt.condition("datum.Shortlisted", alt.value(1.0), alt.value(0.35)),
            tooltip=[
                "Rank:Q",
                "Vendor:N",
                "Criterion:N",
                "Value:N",
                alt.Tooltip("Criterion score:Q", title="Criterion score (0–100)"),
                "Weighted points:Q",
                "Total score:Q",
            ],
        )
        .properties(height=alt.Step(32))
    )
    st.altair_chart(chart, width="stretch")


def render_table(ranked: pd.DataFrame) -> None:
    st.subheader("Full scoring table")
    table = pd.DataFrame(
        {
            "Rank": ranked["rank"],
            "Vendor": ranked["vendor_name"],
            "Total score": ranked["total_score"].round(1),
            **{f"{c.label} score": ranked[score_col(c.key)].round(1) for c in CRITERIA},
            "Unit cost ($)": ranked["unit_cost"],
            "Quality (1–5)": ranked["quality_rating"],
            "Lead time (days)": ranked["lead_time_days"],
            "Region": ranked["region"],
        }
    )
    st.dataframe(
        table,
        hide_index=True,
        column_config={
            "Unit cost ($)": st.column_config.NumberColumn(format="$%.2f"),
            "Quality (1–5)": st.column_config.NumberColumn(format="%.1f"),
            "Lead time (days)": st.column_config.NumberColumn(format="%d"),
            "Total score": st.column_config.ProgressColumn(
                min_value=0, max_value=100, format="%.1f"
            ),
        },
    )
    st.download_button(
        "Download ranking (CSV)",
        data=table.to_csv(index=False),
        file_name="vendor_ranking.csv",
        mime="text/csv",
    )


def render_methodology() -> None:
    with st.expander("How scoring works"):
        st.markdown(
            """
1. **Normalize.** Each criterion is rescaled to a 0–100 score across the vendors being
   compared: the best value gets 100 and the worst gets 0. For cost and lead time lower is
   better, so the scale is inverted. If every vendor has the same value, all get 100.
2. **Weight.** Your slider values are rescaled to sum to 100%. Each criterion score is
   multiplied by its weight, giving the *weighted points* shown in the breakdown chart.
3. **Rank.** A vendor's total score (0–100) is the sum of its weighted points. Ties are
   broken by lower unit cost, then by name.
4. **Explain.** Each rationale lists the vendor's strengths (best on a criterion, or a
   criterion score ≥ 70), weaknesses (score ≤ 30), the criterion contributing most to its
   total, and how it compares with the next vendor in the ranking.

Constraints are applied *before* scoring, so scores are relative to the eligible vendors only.
"""
        )


def main() -> None:
    st.set_page_config(page_title="Vendor Selection Recommender", page_icon="📦", layout="wide")
    init_state()

    st.title("Vendor Selection Recommender")
    st.caption(
        "Scores vendors on cost, quality and lead time using the weights you choose, "
        "then explains the ranked shortlist."
    )

    try:
        vendors = get_vendors()
    except (OSError, ValueError) as exc:
        st.error(f"Could not load vendor data: {exc}")
        st.stop()

    weights, shortlist_size, constraints = sidebar(len(vendors))
    eligible, excluded = apply_constraints(vendors, **constraints)

    if eligible.empty:
        st.error("No vendors meet your constraints. Relax them in the sidebar to see a ranking.")
    else:
        ranked = score_vendors(eligible, weights)
        top = ranked.iloc[0]
        c1, c2, c3 = st.columns([1, 2, 1])
        c1.metric("Vendors evaluated", f"{len(ranked)} of {len(vendors)}")
        c2.metric("Top pick", top["vendor_name"])
        c3.metric("Top score", f"{top['total_score']:.1f} / 100")

        render_shortlist(ranked, shortlist_size, weights)
        render_breakdown_chart(ranked, shortlist_size)
        render_table(ranked)

    if not excluded.empty:
        st.subheader("Excluded by constraints")
        st.dataframe(
            excluded.rename(columns={"vendor_name": "Vendor", "reason": "Reason"}),
            hide_index=True,
        )

    render_methodology()


main()
