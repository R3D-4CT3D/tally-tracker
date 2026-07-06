import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, stash_household_for_rate_limit, verify_csrf
from app.core.config import get_settings
from app.core.db import get_db
from app.core.limiter import import_rate_limit_key, limiter
from app.core.redis import get_redis
from app.models.import_batch import ImportBatch
from app.schemas.import_profiles import ImportProfileCreate
from app.schemas.imports import (
    ImportBatchOut,
    ImportCommitRequest,
    ImportPasteRequest,
    ImportPreviewRequest,
    ImportPreviewResponse,
    ImportPreviewRow,
    ImportUploadResponse,
)
from app.services.board import record_checkin
from app.services.import_parsing import ImportParsingError, sniff_encoding_and_decode
from app.services.import_profiles import create_import_profile, get_import_profile
from app.services.import_sessions import delete_import_session, get_import_session
from app.services.imports import (
    UndoWindowExpiredError,
    batch_is_undoable,
    build_preview,
    commit_import,
    list_import_batches,
    start_import_session,
    undo_import_batch,
)
from app.services.transactions import DuplicateTransactionError, InvalidReferenceError

router = APIRouter(prefix="/imports", tags=["imports"])
settings = get_settings()


def _to_batch_out(batch: ImportBatch) -> ImportBatchOut:
    return ImportBatchOut(
        id=batch.id,
        filename=batch.filename,
        row_count=batch.row_count,
        imported_count=batch.imported_count,
        skipped_dupes=batch.skipped_dupes,
        auto_categorized_count=batch.auto_categorized_count,
        created_at=batch.created_at,
        undoable=batch_is_undoable(batch, settings.import_undo_window_hours),
    )


@router.post(
    "/upload",
    response_model=ImportUploadResponse,
    dependencies=[Depends(verify_csrf), Depends(stash_household_for_rate_limit)],
)
@limiter.limit(settings.import_rate_limit, key_func=import_rate_limit_key)
async def upload_import_route(
    request: Request,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[Redis, Depends(get_redis)],
    file: Annotated[UploadFile, File()],
    profile_id: Annotated[uuid.UUID | None, Form()] = None,
) -> ImportUploadResponse:
    content = await file.read(settings.import_max_file_bytes + 1)
    if len(content) > settings.import_max_file_bytes:
        raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, "File exceeds the 5 MB limit")

    try:
        text = sniff_encoding_and_decode(content)
    except ImportParsingError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc

    profile = None
    if profile_id is not None:
        profile = await get_import_profile(
            db, household_id=uuid.UUID(current_user.household_id), profile_id=profile_id
        )
        if profile is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Import profile not found")

    try:
        _, response = await start_import_session(
            db,
            redis,
            household_id=uuid.UUID(current_user.household_id),
            raw_text=text,
            filename=file.filename,
            source="csv",
            profile=profile,
            session_ttl_seconds=settings.import_session_ttl_seconds,
            max_rows=settings.import_max_rows,
        )
    except ImportParsingError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc

    return response


@router.post(
    "/paste",
    response_model=ImportUploadResponse,
    dependencies=[Depends(verify_csrf), Depends(stash_household_for_rate_limit)],
)
@limiter.limit(settings.import_rate_limit, key_func=import_rate_limit_key)
async def paste_import_route(
    request: Request,
    payload: ImportPasteRequest,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[Redis, Depends(get_redis)],
) -> ImportUploadResponse:
    if len(payload.text.encode("utf-8")) > settings.import_max_file_bytes:
        raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, "Pasted text exceeds the 5 MB limit")

    profile = None
    if payload.profile_id is not None:
        profile = await get_import_profile(
            db, household_id=uuid.UUID(current_user.household_id), profile_id=payload.profile_id
        )
        if profile is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Import profile not found")

    try:
        _, response = await start_import_session(
            db,
            redis,
            household_id=uuid.UUID(current_user.household_id),
            raw_text=payload.text,
            filename=None,
            source="paste",
            profile=profile,
            session_ttl_seconds=settings.import_session_ttl_seconds,
            max_rows=settings.import_max_rows,
        )
    except ImportParsingError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc

    return response


@router.post("/{session_id}/preview", response_model=ImportPreviewResponse)
async def preview_import_route(
    session_id: str,
    payload: ImportPreviewRequest,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[Redis, Depends(get_redis)],
) -> ImportPreviewResponse:
    session = await get_import_session(
        redis, session_id=session_id, household_id=uuid.UUID(current_user.household_id)
    )
    if session is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Import session not found or expired")

    try:
        rows = await build_preview(
            db,
            household_id=uuid.UUID(current_user.household_id),
            session=session,
            mapping=payload.column_mapping,
            date_format=payload.date_format,
            account_id=payload.account_id,
            fuzzy_threshold=settings.fuzzy_match_threshold,
            regex_timeout=settings.regex_match_timeout_seconds,
        )
    except InvalidReferenceError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    except ImportParsingError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc

    preview_rows = [
        ImportPreviewRow(
            row_index=r.row_index,
            date=r.date.isoformat() if r.date is not None else None,
            description=r.description,
            description_display=r.description_display,
            amount_cents=r.amount_cents,
            category_id=r.category_id,
            matched_rule_id=r.matched_rule_id,
            duplicate=r.duplicate,
            error=r.error,
            will_import=r.will_import_by_default,
        )
        for r in rows
    ]
    return ImportPreviewResponse(
        rows=preview_rows,
        valid_count=sum(1 for r in rows if r.error is None),
        error_count=sum(1 for r in rows if r.error is not None),
        exact_duplicate_count=sum(1 for r in rows if r.duplicate == "exact"),
        fuzzy_duplicate_count=sum(1 for r in rows if r.duplicate == "fuzzy"),
    )


@router.post(
    "/{session_id}/commit",
    response_model=ImportBatchOut,
    dependencies=[Depends(verify_csrf), Depends(stash_household_for_rate_limit)],
)
@limiter.limit(settings.import_rate_limit, key_func=import_rate_limit_key)
async def commit_import_route(
    request: Request,
    session_id: str,
    payload: ImportCommitRequest,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[Redis, Depends(get_redis)],
) -> ImportBatchOut:
    session = await get_import_session(
        redis, session_id=session_id, household_id=uuid.UUID(current_user.household_id)
    )
    if session is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Import session not found or expired")

    if payload.source_profile_id is not None:
        profile = await get_import_profile(
            db,
            household_id=uuid.UUID(current_user.household_id),
            profile_id=payload.source_profile_id,
        )
        if profile is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Import profile not found")

    try:
        batch = await commit_import(
            db,
            household_id=uuid.UUID(current_user.household_id),
            user_id=uuid.UUID(current_user.user_id),
            session=session,
            mapping=payload.column_mapping,
            date_format=payload.date_format,
            account_id=payload.account_id,
            overrides=payload.overrides,
            source_profile_id=payload.source_profile_id,
            fuzzy_threshold=settings.fuzzy_match_threshold,
            regex_timeout=settings.regex_match_timeout_seconds,
        )
    except InvalidReferenceError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    except ImportParsingError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    except DuplicateTransactionError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc

    if payload.save_profile_name:
        await create_import_profile(
            db,
            household_id=uuid.UUID(current_user.household_id),
            payload=ImportProfileCreate(
                name=payload.save_profile_name,
                column_mapping=payload.column_mapping,
                date_format=payload.date_format,
            ),
        )

    await delete_import_session(redis, session_id)
    await record_checkin(
        db,
        household_id=uuid.UUID(current_user.household_id),
        user_id=uuid.UUID(current_user.user_id),
    )
    await db.commit()
    return _to_batch_out(batch)


@router.get("/batches", response_model=list[ImportBatchOut])
async def list_import_batches_route(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[ImportBatchOut]:
    batches = await list_import_batches(db, household_id=uuid.UUID(current_user.household_id))
    return [_to_batch_out(b) for b in batches]


@router.delete(
    "/batches/{batch_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(verify_csrf)],
)
async def undo_import_batch_route(
    batch_id: uuid.UUID,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    try:
        deleted = await undo_import_batch(
            db,
            household_id=uuid.UUID(current_user.household_id),
            batch_id=batch_id,
            undo_window_hours=settings.import_undo_window_hours,
        )
    except UndoWindowExpiredError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    if not deleted:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Import batch not found")
    await db.commit()
