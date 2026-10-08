from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

APP_PATH = str(Path(__file__).resolve().parent.parent / "app.py")


@pytest.fixture
def app() -> AppTest:
    at = AppTest.from_file(APP_PATH, default_timeout=30)
    at.run()
    assert not at.exception, at.exception
    return at


def top_pick(at: AppTest) -> str:
    return next(m.value for m in at.metric if m.label == "Top pick")


def test_renders_default_shortlist(app):
    assert app.selectbox(key="preset").value == "Balanced"
    assert app.subheader[0].value == "Ranked shortlist — top 5"
    assert len([m for m in app.metric if m.label == "Score"]) == 5
    assert any("**Why #1:**" in md.value for md in app.markdown)


def test_switching_preset_changes_top_pick(app):
    picks = set()
    for preset in ("Cost-focused", "Quality-focused", "Speed-focused"):
        app.selectbox(key="preset").set_value(preset).run()
        assert not app.exception
        picks.add(top_pick(app))
    assert len(picks) == 3


def test_moving_a_slider_switches_to_custom(app):
    app.slider(key="weight_unit_cost").set_value(90).run()
    assert app.selectbox(key="preset").value == "Custom"
    assert app.slider(key="weight_quality_rating").value == 33


def test_all_zero_weights_warns(app):
    for key in ("weight_unit_cost", "weight_quality_rating", "weight_lead_time_days"):
        app.slider(key=key).set_value(0).run()
    assert not app.exception
    assert any("weighted equally" in w.value for w in app.warning)


def test_impossible_constraints_show_error(app):
    app.number_input[0].set_value(1.0).run()  # max unit cost $1
    assert not app.exception
    assert any("No vendors meet your constraints" in e.value for e in app.error)
