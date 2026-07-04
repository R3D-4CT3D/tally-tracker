import csv
import io
import re
from datetime import date
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Literal

from charset_normalizer import from_bytes

DateFormat = Literal["MDY", "DMY", "YMD"]

_MAX_SNIFF_SAMPLE_CHARS = 65536
_PRINTABLE_RATIO_THRESHOLD = 0.85
_DELIMITER_CANDIDATES = ",;\t|"
_DATE_SPLIT_RE = re.compile(r"[/\-.]")

_DATE_HEADER_HINTS = ["date", "posted", "transaction date", "trans date"]
_DESCRIPTION_HEADER_HINTS = ["description", "memo", "payee", "name", "details"]
_AMOUNT_HEADER_HINTS = ["amount", "value", "debit", "credit"]


class ImportParsingError(Exception):
    """File/content-level problems -- bad encoding, binary content, empty
    file. Per-row problems are never raised; they're recorded as a string
    on that row instead, since one bad row shouldn't block importing the
    other 9,999 (see app/services/imports.py).
    """


def sniff_encoding_and_decode(raw: bytes) -> str:
    """Content-based validation, not extension-trust: a NUL byte or a low
    printable-character ratio means this isn't text at all, regardless of
    what the filename or client-supplied Content-Type claims.
    """
    if b"\x00" in raw:
        raise ImportParsingError("This doesn't look like a valid CSV file.")

    if raw.startswith(b"\xef\xbb\xbf"):
        text = raw.decode("utf-8-sig")
    else:
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            match = from_bytes(raw).best()
            if match is None:
                raise ImportParsingError("Could not determine the file's text encoding.") from None
            text = str(match)

    sample = text[:_MAX_SNIFF_SAMPLE_CHARS]
    if sample:
        printable = sum(1 for ch in sample if ch.isprintable() or ch in "\r\n\t")
        if printable / len(sample) < _PRINTABLE_RATIO_THRESHOLD:
            raise ImportParsingError("This doesn't look like a valid CSV file.")
    return text


def sniff_dialect_and_parse(text: str) -> tuple[list[str], list[list[str]]]:
    if not text.strip("﻿\r\n \t"):
        raise ImportParsingError("File appears to be empty.")

    sample = text[:_MAX_SNIFF_SAMPLE_CHARS]
    try:
        dialect: type[csv.Dialect] | csv.Dialect = csv.Sniffer().sniff(
            sample, delimiters=_DELIMITER_CANDIDATES
        )
    except csv.Error:
        dialect = csv.excel

    reader = csv.reader(io.StringIO(text), dialect)
    rows = [row for row in reader if any(cell.strip() for cell in row)]
    if len(rows) < 2:
        raise ImportParsingError("File must have a header row and at least one data row.")
    header, *data_rows = rows
    return header, data_rows


def parse_amount_to_cents(raw: str) -> int:
    """Never float multiplication -- Decimal is exact for base-10 input, the
    same invariant the frontend's lib/money.ts enforces via string/int math.
    """
    text = raw.strip()
    if not text:
        raise ValueError("Amount is empty")

    negative = False
    if text.startswith("(") and text.endswith(")"):
        negative = True
        text = text[1:-1].strip()
    if text.startswith("-"):
        negative = not negative
        text = text[1:].strip()
    elif text.endswith("-"):
        negative = not negative
        text = text[:-1].strip()

    cleaned = re.sub(r"[^0-9.]", "", text)
    if not cleaned or cleaned.count(".") > 1:
        raise ValueError(f"Could not parse amount: {raw!r}")

    try:
        value = Decimal(cleaned)
    except InvalidOperation as exc:
        raise ValueError(f"Could not parse amount: {raw!r}") from exc

    cents = int((value * 100).to_integral_value(rounding=ROUND_HALF_UP))
    return -cents if negative else cents


def parse_date(raw: str, fmt: DateFormat) -> date:
    text = raw.strip()
    parts = _DATE_SPLIT_RE.split(text)
    if len(parts) != 3:
        raise ValueError(f"Could not parse date: {raw!r}")

    a, b, c = parts
    if fmt == "YMD":
        year, month, day = a, b, c
    elif fmt == "MDY":
        month, day, year = a, b, c
    else:
        day, month, year = a, b, c

    try:
        year_i, month_i, day_i = int(year), int(month), int(day)
    except ValueError as exc:
        raise ValueError(f"Could not parse date: {raw!r}") from exc

    if len(year) <= 2:
        year_i += 2000 if year_i < 70 else 1900

    try:
        return date(year_i, month_i, day_i)
    except ValueError as exc:
        raise ValueError(f"Could not parse date: {raw!r}") from exc


def detect_date_format(samples: list[str]) -> tuple[DateFormat, bool]:
    """Returns (best_guess, ambiguous). ambiguous=True means the evidence in
    `samples` cannot distinguish MM/DD from DD/MM -- the caller (the column-
    mapping step of the wizard) must make the user confirm explicitly rather
    than silently guessing, per spec §4.3.
    """
    saw_year_first = False
    definite_mdy = False
    definite_dmy = False

    for sample in samples:
        parts = _DATE_SPLIT_RE.split(sample.strip())
        if len(parts) != 3:
            continue
        a, b, _c = parts
        if len(a) == 4:
            saw_year_first = True
            continue
        try:
            first, second = int(a), int(b)
        except ValueError:
            continue
        if first > 12:
            definite_dmy = True
        elif second > 12:
            definite_mdy = True

    if saw_year_first:
        return "YMD", False
    if definite_dmy and not definite_mdy:
        return "DMY", False
    if definite_mdy and not definite_dmy:
        return "MDY", False
    # Either no sample disambiguated at all, or samples contradict each
    # other (mixed formats within one column) -- can't trust the signal.
    return "MDY", True


def detect_column_mapping(header: list[str]) -> dict[str, str | None]:
    lowered = [h.strip().lower() for h in header]

    def find(hints: list[str]) -> str | None:
        for hint in hints:
            for original, low in zip(header, lowered, strict=True):
                if hint in low:
                    return original
        return None

    return {
        "date": find(_DATE_HEADER_HINTS),
        "description": find(_DESCRIPTION_HEADER_HINTS),
        "amount": find(_AMOUNT_HEADER_HINTS),
    }
