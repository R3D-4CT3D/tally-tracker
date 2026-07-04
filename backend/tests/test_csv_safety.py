import pytest

from app.services.csv_safety import sanitize_csv_cell


@pytest.mark.parametrize(
    "value",
    [
        "=cmd|'/c calc'!A1",
        "+1+1",
        "-1+1",
        "@SUM(A1:A2)",
    ],
)
def test_sanitize_csv_cell_prefixes_dangerous_values(value: str) -> None:
    result = sanitize_csv_cell(value)
    assert result == f"'{value}"
    assert result.startswith("'")


@pytest.mark.parametrize("value", ["Grocery Store", "123.45", "", "Coffee Shop - January"])
def test_sanitize_csv_cell_leaves_normal_values_untouched(value: str) -> None:
    assert sanitize_csv_cell(value) == value
