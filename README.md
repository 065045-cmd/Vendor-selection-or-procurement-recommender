# Vendor Selection / Procurement Recommender

A Streamlit app that scores vendors on **cost**, **quality**, and **lead time**, lets you
adjust how much each criterion matters, and produces a **ranked shortlist with a plain-language
rationale** for every vendor.

## Features

- **Vendor scoring** on cost (lower is better), quality rating (higher is better), and lead
  time (lower is better).
- **Adjustable weighted criteria**: start from a preset (Balanced, Cost-, Quality-, or
  Speed-focused) and fine-tune with sliders. Weights are rescaled to sum to 100%.
- **Ranked shortlist with rationale**: each shortlisted vendor shows its score, its strengths
  and weaknesses, the criterion driving its score, and why it ranks above or below its
  neighbour (for example, "Leads #2 BrightLine Components by 0.5 pts, mainly on cost (+7.2)
  despite trailing on quality (−12.2)").
- **Score breakdown chart** showing the weighted points each vendor earns per criterion.
- **Optional constraints** (max unit cost, min quality, max lead time) that exclude vendors
  before scoring.
- **Full scoring table** with a CSV download.

The app ships with a sample dataset of 10 fictional vendors in `data/sample_vendors.csv`.

## Getting started

Requires Python 3.10+.

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

Then open http://localhost:8501.

## Running tests

```bash
pip install -r requirements-dev.txt
pytest
```

The tests cover the scoring engine, the rationale text, data validation, and an end-to-end
run of the Streamlit app (via `streamlit.testing`).

## How scoring works

1. **Normalize**: each criterion is min-max scaled to 0–100 across the vendors being compared
   (best value = 100, worst = 0; inverted for cost and lead time). If every vendor has the
   same value, all get 100.
2. **Weight**: each criterion score is multiplied by its normalized weight to give
   *weighted points*.
3. **Rank**: total score (0–100) is the sum of weighted points. Ties are broken by lower
   unit cost, then vendor name.
4. **Explain**: the rationale flags strengths (best on a criterion, or criterion score ≥ 70),
   weaknesses (≤ 30), the biggest contributor to the total, and the per-criterion difference
   with the adjacent vendor in the ranking.

## Project layout

```
app.py                     Streamlit UI
vendor_recommender/
  criteria.py              Criterion definitions and weight presets
  data.py                  CSV loading and validation
  scoring.py               Normalization, weighting, ranking, constraints
  rationale.py             Rationale text for each vendor
data/sample_vendors.csv    Sample vendor dataset
tests/                     pytest suite
```

## Vendor data format

| column           | type   | notes                     |
|------------------|--------|---------------------------|
| `vendor_name`    | text   | must be unique            |
| `region`         | text   | shown for context only    |
| `unit_cost`      | number | > 0, in USD               |
| `quality_rating` | number | 1–5                       |
| `lead_time_days` | number | ≥ 0                       |

To use your own data, replace `data/sample_vendors.csv` with a file in this format.
