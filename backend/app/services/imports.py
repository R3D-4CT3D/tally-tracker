import hashlib
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from datetime import date as date_type
from difflib import SequenceMatcher
from typing import Literal

from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import Account
from app.models.import_batch import ImportBatch
from app.models.import_profile import ImportProfile
from app.models.transaction import Transaction
from app.schemas.imports import ColumnMapping, DateFormat, ImportUploadResponse
from app.services.accounts import get_account
from app.services.bank_formats import detect_bank_format
from app.services.builtin_categorization import build_builtin_rules
from app.services.import_parsing import (
    ImportParsingError,
    detect_column_mapping,
    detect_date_format,
    parse_amount_to_cents,
    parse_date,
    sniff_dialect_and_parse,
)
from app.services.import_sessions import ImportSessionData, create_import_session
from app.services.rules import apply_rules, list_rules
from app.services.transactions import (
    DuplicateTransactionError,
    InvalidReferenceError,
    compute_dedupe_hash,
    normalize_description,
)

_SAMPLE_ROWS_LIMIT = 20


class UndoWindowExpiredError(Exception):
    """Raised when a batch undo is attempted past the configured window."""


@dataclass
class ProcessedRow:
    row_index: int
    date: date_type | None = None
    description: str | None = None
    description_display: str | None = None
    amount_cents: int | None = None
    dedupe_hash: str | None = None
    category_id: uuid.UUID | None = None
    matched_rule_id: uuid.UUID | None = None
    duplicate: Literal["exact", "fuzzy"] | None = None
    error: str | None = None

    @property
    def will_import_by_default(self) -> bool:
        if self.error is not None:
            return False
        return self.duplicate != "exact"


async def _suggest_account_from_last_four(
    db: AsyncSession, *, household_id: uuid.UUID, last_four: str
) -> uuid.UUID | None:
    stmt = select(Account.id).where(
        Account.household_id == household_id, Account.last_four == last_four
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def start_import_session(
    db: AsyncSession,
    redis: Redis,
    *,
    household_id: uuid.UUID,
    raw_text: str,
    filename: str | None,
    source: Literal["csv", "paste"],
    profile: ImportProfile | None,
    session_ttl_seconds: int,
    max_rows: int,
) -> tuple[ImportSessionData, ImportUploadResponse]:
    header, rows = sniff_dialect_and_parse(raw_text)
    if len(rows) > max_rows:
        raise ImportParsingError(f"File has too many rows (max {max_rows})")

    session = await create_import_session(
        redis,
        household_id=household_id,
        filename=filename,
        source=source,
        header=header,
        rows=rows,
        ttl_seconds=session_ttl_seconds,
    )

    suggested_mapping: ColumnMapping | None = None
    date_format_suggestion: DateFormat = "MDY"
    date_format_ambiguous = True
    skip_mapping_step = False
    detected_bank_format: str | None = None
    suggested_account_id: uuid.UUID | None = None

    if profile is not None:
        # The user already told us the format by picking a saved profile --
        # no reason to still show a pre-filled mapping form.
        suggested_mapping = ColumnMapping.model_validate(profile.column_mapping)
        date_format_suggestion = profile.date_format  # type: ignore[assignment]
        date_format_ambiguous = False
        skip_mapping_step = True
    else:
        bank_format = detect_bank_format(header)
        if bank_format is not None:
            suggested_mapping = bank_format.mapping
            date_format_suggestion = bank_format.date_format
            date_format_ambiguous = False
            skip_mapping_step = True
            detected_bank_format = bank_format.name

            if bank_format.last_four_column is not None:
                last_four_idx = header.index(bank_format.last_four_column)
                for row in rows:
                    if last_four_idx < len(row) and row[last_four_idx].strip():
                        suggested_account_id = await _suggest_account_from_last_four(
                            db,
                            household_id=household_id,
                            last_four=row[last_four_idx].strip(),
                        )
                        if suggested_account_id is not None:
                            break
        else:
            detected = detect_column_mapping(header)
            if all(detected.values()):
                suggested_mapping = ColumnMapping.model_validate(detected)
                date_column_index = header.index(detected["date"])  # type: ignore[arg-type]
                samples = [
                    row[date_column_index]
                    for row in rows[:_SAMPLE_ROWS_LIMIT]
                    if date_column_index < len(row)
                ]
                date_format_suggestion, date_format_ambiguous = detect_date_format(samples)

    response = ImportUploadResponse(
        import_session_id=session.session_id,
        filename=filename,
        source=source,
        header=header,
        sample_rows=rows[:_SAMPLE_ROWS_LIMIT],
        row_count=len(rows),
        suggested_mapping=suggested_mapping,
        date_format_suggestion=date_format_suggestion,
        date_format_ambiguous=date_format_ambiguous,
        skip_mapping_step=skip_mapping_step,
        detected_bank_format=detected_bank_format,
        suggested_account_id=suggested_account_id,
    )
    return session, response


async def _fetch_existing_hashes(db: AsyncSession, household_id: uuid.UUID) -> set[str]:
    stmt = select(Transaction.dedupe_hash).where(Transaction.household_id == household_id)
    result = await db.execute(stmt)
    return set(result.scalars().all())


async def _check_fuzzy_duplicate(
    db: AsyncSession,
    *,
    household_id: uuid.UUID,
    date: date_type,
    amount_cents: int,
    description: str,
    threshold: float,
) -> bool:
    stmt = select(Transaction.description_raw).where(
        Transaction.household_id == household_id,
        Transaction.date == date,
        Transaction.amount_cents == amount_cents,
    )
    result = await db.execute(stmt)
    normalized_new = normalize_description(description)
    for existing_raw in result.scalars().all():
        ratio = SequenceMatcher(None, normalized_new, normalize_description(existing_raw)).ratio()
        if ratio >= threshold:
            return True
    return False


async def _process_rows(
    db: AsyncSession,
    *,
    household_id: uuid.UUID,
    session: ImportSessionData,
    mapping: ColumnMapping,
    date_format: DateFormat,
    account_id: uuid.UUID,
    fuzzy_threshold: float,
    regex_timeout: float,
) -> list[ProcessedRow]:
    """The single source of truth for row parsing, dedupe-checking, and rule
    application -- both build_preview() and commit_import() call this, so
    what a user sees in preview is exactly what gets committed.
    """
    account = await get_account(db, household_id=household_id, account_id=account_id)
    if account is None:
        raise InvalidReferenceError("Account not found")

    try:
        date_idx = session.header.index(mapping.date)
        description_idx = session.header.index(mapping.description)
        amount_idx = session.header.index(mapping.amount)
    except ValueError as exc:
        raise ImportParsingError(
            f"Column mapping references a column not in the file: {exc}"
        ) from exc

    dedupe_description_idx: int | None = None
    if mapping.dedupe_description is not None:
        try:
            dedupe_description_idx = session.header.index(mapping.dedupe_description)
        except ValueError as exc:
            raise ImportParsingError(
                f"Column mapping references a column not in the file: {exc}"
            ) from exc

    existing_hashes = await _fetch_existing_hashes(db, household_id)
    # Real household rules always win (first-match-wins over list order) --
    # built-in merchant-pattern suggestions are appended after and only fire
    # when nothing the user defined matched.
    rules = await list_rules(db, household_id=household_id)
    rules = rules + await build_builtin_rules(db, household_id=household_id)

    seen_hashes: set[str] = set()
    processed: list[ProcessedRow] = []

    for row_index, row in enumerate(session.rows):
        raw_date = row[date_idx] if date_idx < len(row) else ""
        raw_description = row[description_idx] if description_idx < len(row) else ""
        raw_amount = row[amount_idx] if amount_idx < len(row) else ""
        description = raw_description.strip()

        error: str | None = None
        parsed_date: date_type | None = None
        parsed_amount: int | None = None

        if not description:
            error = "Description is empty"
        else:
            try:
                parsed_date = parse_date(raw_date, date_format)
            except ValueError as exc:
                error = str(exc)
            if error is None:
                try:
                    parsed_amount = parse_amount_to_cents(raw_amount)
                except ValueError as exc:
                    error = str(exc)

        if error is not None or parsed_date is None or parsed_amount is None:
            processed.append(
                ProcessedRow(row_index=row_index, error=error or "Could not parse row")
            )
            continue

        dedupe_description = description
        if dedupe_description_idx is not None:
            raw_dedupe_description = (
                row[dedupe_description_idx] if dedupe_description_idx < len(row) else ""
            )
            # Falls back to the display description if this row's dedupe
            # column happens to be blank, rather than hashing an empty string.
            dedupe_description = raw_dedupe_description.strip() or description

        dedupe_hash = compute_dedupe_hash(
            household_id=household_id,
            account_id=account_id,
            date=parsed_date,
            amount_cents=parsed_amount,
            description=dedupe_description,
        )
        duplicate: Literal["exact", "fuzzy"] | None = None
        if dedupe_hash in existing_hashes or dedupe_hash in seen_hashes:
            duplicate = "exact"
        seen_hashes.add(dedupe_hash)

        if duplicate is None and await _check_fuzzy_duplicate(
            db,
            household_id=household_id,
            date=parsed_date,
            amount_cents=parsed_amount,
            description=description,
            threshold=fuzzy_threshold,
        ):
            duplicate = "fuzzy"

        # Rule/built-in-pattern matching searches the display description
        # *and* the raw dedupe description when they differ -- bank exports
        # (Wells Fargo included) often show a generic display description
        # ("REFUNDED TO WELLS FARGO CARD") while the raw merchant name
        # carries the actual identifying text ("AMAZON.COM REFUND"). Appended,
        # not replaced, so "starts_with" rules still anchor on the display
        # text's actual start.
        match_description = (
            description
            if dedupe_description == description
            else f"{description} {dedupe_description}"
        )
        matched_rule = apply_rules(
            rules,
            description=match_description,
            amount_cents=parsed_amount,
            account_id=account_id,
            timeout=regex_timeout,
        )
        description_display = (
            matched_rule.set_display_name
            if matched_rule is not None and matched_rule.set_display_name
            else description
        )

        processed.append(
            ProcessedRow(
                row_index=row_index,
                date=parsed_date,
                description=description,
                description_display=description_display,
                amount_cents=parsed_amount,
                dedupe_hash=dedupe_hash,
                category_id=matched_rule.set_category_id if matched_rule is not None else None,
                matched_rule_id=matched_rule.id if matched_rule is not None else None,
                duplicate=duplicate,
                error=None,
            )
        )

    return processed


async def build_preview(
    db: AsyncSession,
    *,
    household_id: uuid.UUID,
    session: ImportSessionData,
    mapping: ColumnMapping,
    date_format: DateFormat,
    account_id: uuid.UUID,
    fuzzy_threshold: float,
    regex_timeout: float,
) -> list[ProcessedRow]:
    return await _process_rows(
        db,
        household_id=household_id,
        session=session,
        mapping=mapping,
        date_format=date_format,
        account_id=account_id,
        fuzzy_threshold=fuzzy_threshold,
        regex_timeout=regex_timeout,
    )


async def commit_import(
    db: AsyncSession,
    *,
    household_id: uuid.UUID,
    user_id: uuid.UUID,
    session: ImportSessionData,
    mapping: ColumnMapping,
    date_format: DateFormat,
    account_id: uuid.UUID,
    overrides: dict[str, bool],
    source_profile_id: uuid.UUID | None,
    fuzzy_threshold: float,
    regex_timeout: float,
) -> ImportBatch:
    processed = await _process_rows(
        db,
        household_id=household_id,
        session=session,
        mapping=mapping,
        date_format=date_format,
        account_id=account_id,
        fuzzy_threshold=fuzzy_threshold,
        regex_timeout=regex_timeout,
    )

    batch = ImportBatch(
        household_id=household_id,
        user_id=user_id,
        source_profile_id=source_profile_id,
        filename=session.filename,
        row_count=len(processed),
        imported_count=0,
        skipped_dupes=0,
    )
    db.add(batch)
    await db.flush()

    imported_count = 0
    skipped_dupes = 0
    auto_categorized_count = 0

    for row in processed:
        override = overrides.get(str(row.row_index))
        will_import = row.will_import_by_default if override is None else override
        if row.error is not None:
            will_import = False

        if not will_import:
            if row.duplicate == "exact":
                skipped_dupes += 1
            continue

        assert row.date is not None
        assert row.amount_cents is not None
        assert row.description is not None
        assert row.description_display is not None
        assert row.dedupe_hash is not None

        row_dedupe_hash = row.dedupe_hash
        if row.duplicate == "exact":
            # Forced-include despite matching an existing transaction (or an
            # earlier row in this same file): the *base* hash can't be
            # reused verbatim, since household_id+dedupe_hash is uniquely
            # constrained at the DB level and the row it matches already
            # occupies that value. Salting with this commit's own batch id
            # (fresh per commit) and the row's index (unique within one
            # file) keeps the stored value deterministic and collision-free,
            # including if the identical file is re-imported-with-override
            # again later.
            row_dedupe_hash = hashlib.sha256(
                f"{row.dedupe_hash}:{batch.id}:{row.row_index}".encode()
            ).hexdigest()

        transaction = Transaction(
            household_id=household_id,
            account_id=account_id,
            date=row.date,
            amount_cents=row.amount_cents,
            description_raw=row.description,
            description_display=row.description_display,
            category_id=row.category_id,
            source=session.source,
            dedupe_hash=row_dedupe_hash,
            created_by=user_id,
            import_batch_id=batch.id,
        )
        db.add(transaction)
        imported_count += 1
        if row.category_id is not None:
            # There's no manual category-override step in the wizard today
            # -- every non-null category_id on a committed row came from a
            # rule match, real (user-defined) or built-in merchant pattern.
            auto_categorized_count += 1

    batch.imported_count = imported_count
    batch.skipped_dupes = skipped_dupes
    batch.auto_categorized_count = auto_categorized_count

    try:
        await db.flush()
    except IntegrityError as exc:
        await db.rollback()
        raise DuplicateTransactionError(
            "A duplicate transaction was detected while committing this batch"
        ) from exc

    return batch


def batch_is_undoable(batch: ImportBatch, undo_window_hours: int) -> bool:
    return datetime.now(UTC) - batch.created_at <= timedelta(hours=undo_window_hours)


async def list_import_batches(db: AsyncSession, *, household_id: uuid.UUID) -> list[ImportBatch]:
    stmt = (
        select(ImportBatch)
        .where(ImportBatch.household_id == household_id)
        .order_by(ImportBatch.created_at.desc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def undo_import_batch(
    db: AsyncSession, *, household_id: uuid.UUID, batch_id: uuid.UUID, undo_window_hours: int
) -> bool:
    stmt = select(ImportBatch).where(
        ImportBatch.household_id == household_id, ImportBatch.id == batch_id
    )
    result = await db.execute(stmt)
    batch = result.scalar_one_or_none()
    if batch is None:
        return False

    if not batch_is_undoable(batch, undo_window_hours):
        raise UndoWindowExpiredError("This import batch can no longer be undone")

    await db.delete(batch)
    await db.flush()
    return True
