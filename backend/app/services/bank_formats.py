"""Registry of known bank CSV export formats, matched by exact header
signature -- checked before falling back to the generic column-name-hint
heuristic in app/services/import_parsing.py's detect_column_mapping. A
match means the wizard can skip the manual column-mapping step entirely
(see ImportUploadResponse.skip_mapping_step).
"""

from dataclasses import dataclass

from app.schemas.imports import ColumnMapping, DateFormat


@dataclass(frozen=True)
class BankFormat:
    name: str
    header: tuple[str, ...]
    mapping: ColumnMapping
    date_format: DateFormat
    # Column holding the card/account last-4 digits, if any -- used for
    # account auto-suggest (app/services/imports.py). Not one of
    # ColumnMapping's three canonical roles, so it's tracked separately.
    last_four_column: str | None = None


_KNOWN_FORMATS: tuple[BankFormat, ...] = (
    BankFormat(
        name="Wells Fargo Credit Card",
        header=(
            "Transaction Date",
            "Posted Date",
            "Description",
            "Amount",
            "Card Last 4",
            "Name on Card",
            "Raw Merchant Name",
        ),
        mapping=ColumnMapping(
            date="Transaction Date",
            description="Description",
            dedupe_description="Raw Merchant Name",
            amount="Amount",
        ),
        # US bank exports are always month/day/year -- no ambiguity to ask
        # the user to confirm, unlike the generic heuristic path.
        date_format="MDY",
        last_four_column="Card Last 4",
    ),
)


def detect_bank_format(header: list[str]) -> BankFormat | None:
    for fmt in _KNOWN_FORMATS:
        if tuple(header) == fmt.header:
            return fmt
    return None
