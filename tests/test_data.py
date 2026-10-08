import io

import pytest

from vendor_recommender import load_vendors

HEADER = "vendor_name,region,unit_cost,quality_rating,lead_time_days\n"


def load(text: str):
    return load_vendors(io.StringIO(text))


def test_sample_data_loads(sample_vendors):
    assert len(sample_vendors) == 10
    assert sample_vendors["vendor_name"].is_unique
    for col in ("unit_cost", "quality_rating", "lead_time_days"):
        assert sample_vendors[col].dtype == float


def test_extra_columns_dropped_and_names_trimmed():
    df = load(
        " vendor_name , region,unit_cost,quality_rating,lead_time_days,notes\n"
        "  Acme ,EU,10,4,5,hello\n"
        "Beta,US,12,3.5,7,\n"
    )
    assert list(df.columns) == ["vendor_name", "region", "unit_cost", "quality_rating", "lead_time_days"]
    assert df["vendor_name"].iloc[0] == "Acme"


@pytest.mark.parametrize(
    ("body", "message"),
    [
        ("vendor_name,unit_cost\nA,1\nB,2\n", "Missing required column"),
        (HEADER + "A,EU,abc,4,5\nB,EU,10,4,5\n", "non-numeric values \\(CSV row\\(s\\) 2\\)"),
        (HEADER + "A,EU,10,4,5\nB,EU,,4,5\n", "Missing values in column\\(s\\): unit_cost"),
        (HEADER + "A,EU,10,4,5\n , EU,10,4,5\n", "Missing values in column\\(s\\): vendor_name"),
        (HEADER + "A,EU,10,4,5\n", "At least 2 vendors"),
        (HEADER + "A,EU,10,4,5\nA,US,12,4,5\n", "Duplicate vendor name"),
        (HEADER + "A,EU,0,4,5\nB,EU,10,4,5\n", "unit_cost must be greater than 0"),
        (HEADER + "A,EU,10,4,-1\nB,EU,10,4,5\n", "lead_time_days cannot be negative"),
        (HEADER + "A,EU,10,5.5,5\nB,EU,10,4,5\n", "quality_rating must be between 1 and 5"),
    ],
)
def test_invalid_data_rejected(body, message):
    with pytest.raises(ValueError, match=message):
        load(body)
