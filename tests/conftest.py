import pandas as pd
import pytest

from vendor_recommender import load_vendors


@pytest.fixture
def sample_vendors() -> pd.DataFrame:
    return load_vendors()


def make_vendors(rows: list[tuple]) -> pd.DataFrame:
    """Build a vendor table from (name, unit_cost, quality_rating, lead_time_days) tuples."""
    return pd.DataFrame(
        [
            {
                "vendor_name": name,
                "region": "Test",
                "unit_cost": float(cost),
                "quality_rating": float(quality),
                "lead_time_days": float(lead),
            }
            for name, cost, quality, lead in rows
        ]
    )
