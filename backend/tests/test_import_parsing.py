from datetime import date

import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.services.import_parsing import (
    ImportParsingError,
    detect_column_mapping,
    detect_date_format,
    parse_amount_to_cents,
    parse_date,
    sniff_dialect_and_parse,
    sniff_encoding_and_decode,
)

# --- parse_amount_to_cents: property-based (Hypothesis) ---------------------


@given(
    dollars=st.integers(min_value=0, max_value=999_999),
    cents=st.integers(min_value=0, max_value=99),
    negative=st.booleans(),
)
def test_parse_amount_round_trips_plain_decimal(dollars: int, cents: int, negative: bool) -> None:
    value = f"{dollars}.{cents:02d}"
    if negative:
        value = f"-{value}"
    expected = dollars * 100 + cents
    if negative:
        expected = -expected
    assert parse_amount_to_cents(value) == expected


@given(
    dollars=st.integers(min_value=1000, max_value=999_999),
    cents=st.integers(min_value=0, max_value=99),
)
def test_parse_amount_handles_thousands_separator(dollars: int, cents: int) -> None:
    formatted = f"{dollars:,}.{cents:02d}"
    assert parse_amount_to_cents(formatted) == dollars * 100 + cents


@given(
    dollars=st.integers(min_value=0, max_value=999_999),
    cents=st.integers(min_value=0, max_value=99),
)
def test_parse_amount_dollar_sign(dollars: int, cents: int) -> None:
    assert parse_amount_to_cents(f"${dollars}.{cents:02d}") == dollars * 100 + cents


@given(
    dollars=st.integers(min_value=1, max_value=999_999),
    cents=st.integers(min_value=0, max_value=99),
)
def test_parse_amount_parentheses_negative(dollars: int, cents: int) -> None:
    expected = -(dollars * 100 + cents)
    assert parse_amount_to_cents(f"({dollars:,}.{cents:02d})") == expected


@given(
    dollars=st.integers(min_value=1, max_value=999_999),
    cents=st.integers(min_value=0, max_value=99),
)
def test_parse_amount_trailing_minus(dollars: int, cents: int) -> None:
    expected = -(dollars * 100 + cents)
    assert parse_amount_to_cents(f"{dollars}.{cents:02d}-") == expected


def test_parse_amount_whole_dollar_no_decimal() -> None:
    assert parse_amount_to_cents("1234") == 123400


def test_parse_amount_empty_raises() -> None:
    with pytest.raises(ValueError, match="empty"):
        parse_amount_to_cents("")


def test_parse_amount_garbage_raises() -> None:
    with pytest.raises(ValueError):
        parse_amount_to_cents("not a number")


def test_parse_amount_multiple_decimal_points_raises() -> None:
    with pytest.raises(ValueError):
        parse_amount_to_cents("1.2.3")


# --- parse_date: property-based (Hypothesis, round-trip per format) --------


@given(d=st.dates(min_value=date(1925, 1, 1), max_value=date(2099, 12, 31)))
def test_parse_date_mdy_round_trips(d: date) -> None:
    formatted = f"{d.month:02d}/{d.day:02d}/{d.year:04d}"
    assert parse_date(formatted, "MDY") == d


@given(d=st.dates(min_value=date(1925, 1, 1), max_value=date(2099, 12, 31)))
def test_parse_date_dmy_round_trips(d: date) -> None:
    formatted = f"{d.day:02d}/{d.month:02d}/{d.year:04d}"
    assert parse_date(formatted, "DMY") == d


@given(d=st.dates(min_value=date(1925, 1, 1), max_value=date(2099, 12, 31)))
def test_parse_date_ymd_round_trips(d: date) -> None:
    formatted = f"{d.year:04d}-{d.month:02d}-{d.day:02d}"
    assert parse_date(formatted, "YMD") == d


@given(d=st.dates(min_value=date(2000, 1, 1), max_value=date(2069, 12, 31)))
def test_parse_date_two_digit_year(d: date) -> None:
    formatted = f"{d.month:02d}/{d.day:02d}/{d.year % 100:02d}"
    assert parse_date(formatted, "MDY") == d


def test_parse_date_invalid_text_raises() -> None:
    with pytest.raises(ValueError):
        parse_date("not-a-date", "MDY")


def test_parse_date_out_of_range_raises() -> None:
    with pytest.raises(ValueError):
        parse_date("13/45/2024", "MDY")


# --- date-format ambiguity detection -----------------------------------------


def test_detect_date_format_definite_mdy() -> None:
    fmt, ambiguous = detect_date_format(["01/15/2024", "02/20/2024"])
    assert fmt == "MDY"
    assert ambiguous is False


def test_detect_date_format_definite_dmy() -> None:
    fmt, ambiguous = detect_date_format(["15/01/2024", "20/02/2024"])
    assert fmt == "DMY"
    assert ambiguous is False


def test_detect_date_format_ymd_unambiguous() -> None:
    fmt, ambiguous = detect_date_format(["2024-01-15", "2024-02-20"])
    assert fmt == "YMD"
    assert ambiguous is False


def test_detect_date_format_ambiguous_when_all_parts_le_12() -> None:
    _, ambiguous = detect_date_format(["01/02/2024", "03/04/2024"])
    assert ambiguous is True


def test_detect_date_format_ambiguous_on_contradictory_samples() -> None:
    # First sample looks DMY-only-possible (15 > 12 in first slot), second
    # looks MDY-only-possible (20 > 12 in second slot) -- contradictory.
    _, ambiguous = detect_date_format(["15/01/2024", "01/20/2024"])
    assert ambiguous is True


# --- delimiter sniffing + row parsing ----------------------------------------


def test_sniff_dialect_comma() -> None:
    header, rows = sniff_dialect_and_parse("a,b,c\n1,2,3\n")
    assert header == ["a", "b", "c"]
    assert rows == [["1", "2", "3"]]


def test_sniff_dialect_tab() -> None:
    header, rows = sniff_dialect_and_parse("a\tb\tc\n1\t2\t3\n")
    assert header == ["a", "b", "c"]
    assert rows == [["1", "2", "3"]]


def test_sniff_dialect_semicolon() -> None:
    header, rows = sniff_dialect_and_parse("a;b;c\n1;2;3\n")
    assert header == ["a", "b", "c"]


def test_sniff_dialect_quoted_field_with_embedded_comma() -> None:
    header, rows = sniff_dialect_and_parse('a,b\n"1,200.00",text\n')
    assert rows == [["1,200.00", "text"]]


def test_sniff_dialect_empty_raises() -> None:
    with pytest.raises(ImportParsingError):
        sniff_dialect_and_parse("")


def test_sniff_dialect_header_only_raises() -> None:
    with pytest.raises(ImportParsingError):
        sniff_dialect_and_parse("a,b,c\n")


def test_sniff_dialect_skips_trailing_blank_lines() -> None:
    header, rows = sniff_dialect_and_parse("a,b\n1,2\n\n\n")
    assert header == ["a", "b"]
    assert rows == [["1", "2"]]


# --- encoding sniffing --------------------------------------------------------


def test_sniff_encoding_utf8_bom() -> None:
    raw = "Date,Amount\n01/01/2024,10.00\n".encode("utf-8-sig")
    text = sniff_encoding_and_decode(raw)
    assert text.startswith("Date,Amount")


def test_sniff_encoding_plain_utf8() -> None:
    raw = "Café,Amount\n".encode()
    text = sniff_encoding_and_decode(raw)
    assert "Café" in text


def test_sniff_encoding_latin1_fallback_does_not_raise() -> None:
    raw = "Cafe Resume,10.00\n".encode("latin-1")
    text = sniff_encoding_and_decode(raw)
    assert "10.00" in text


def test_sniff_encoding_nul_byte_rejected() -> None:
    with pytest.raises(ImportParsingError):
        sniff_encoding_and_decode(b"hello\x00world")


def test_sniff_encoding_binary_content_rejected() -> None:
    with pytest.raises(ImportParsingError):
        sniff_encoding_and_decode(bytes(range(256)))


# --- column mapping auto-detect ----------------------------------------------


def test_detect_column_mapping_standard_headers() -> None:
    mapping = detect_column_mapping(["Date", "Description", "Amount"])
    assert mapping == {"date": "Date", "description": "Description", "amount": "Amount"}


def test_detect_column_mapping_bank_style_headers() -> None:
    mapping = detect_column_mapping(["Posted Date", "Payee", "Debit"])
    assert mapping["date"] == "Posted Date"
    assert mapping["description"] == "Payee"
    assert mapping["amount"] == "Debit"


def test_detect_column_mapping_no_match_returns_none() -> None:
    mapping = detect_column_mapping(["Foo", "Bar", "Baz"])
    assert mapping == {"date": None, "description": None, "amount": None}
