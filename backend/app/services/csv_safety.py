_DANGEROUS_PREFIXES = ("=", "+", "-", "@")


def sanitize_csv_cell(value: str) -> str:
    """Prefixes formula-injection-dangerous cells with a leading apostrophe.

    Excel/Sheets/LibreOffice all treat a cell starting with =, +, -, or @ as
    the start of a formula when a CSV is opened -- a maliciously crafted
    transaction description (e.g. `=cmd|'/c calc'!A1`) could otherwise
    execute when a household exports and later re-opens their own data.

    Not wired into any export endpoint yet -- CSV/JSON export is out of
    scope until V2 per docs/TALLY_BUILD_SPEC.md §4.3 -- but the defense is
    written and unit-tested now per the spec's explicit instruction to
    "note this in code even though export is V2," so it isn't forgotten
    when export actually ships.
    """
    if value.startswith(_DANGEROUS_PREFIXES):
        return f"'{value}"
    return value
