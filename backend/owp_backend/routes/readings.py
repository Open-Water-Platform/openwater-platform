"""Reading routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, status

from owp_backend.db import ReadingRow
from owp_backend.dependencies import DatabaseDep, SettingsDep
from owp_backend.errors import device_not_found, reading_not_found
from owp_backend.schemas import (
    PaginatedReadingsOut,
    ReadingOut,
    ReadingsQueryParams,
    SortOrder,
)

router = APIRouter(
    prefix="/api/v1/devices/{device_id}/readings",
    tags=["readings"],
)


def _reading_to_out(row: ReadingRow) -> ReadingOut:
    return ReadingOut(
        device_id=row.device_id,
        recorded_at=row.recorded_at,
        parameter=row.parameter,
        value=row.value,
        unit=row.unit,
    )


def _resolve_page_limit(requested: int | None, default: int, maximum: int) -> int:
    page_limit = requested or default
    return min(page_limit, maximum)


async def _ensure_device_exists(database: DatabaseDep, device_id: str) -> None:
    if not await database.device_exists(device_id):
        raise device_not_found(device_id)


@router.get("", response_model=PaginatedReadingsOut)
async def list_readings(
    device_id: str,
    database: DatabaseDep,
    settings: SettingsDep,
    recorded_from: str | None = Query(default=None, alias="from"),
    recorded_to: str | None = Query(default=None, alias="to"),
    parameter: str | None = Query(default=None),
    limit: int | None = Query(default=None, ge=1),
    offset: int = Query(default=0, ge=0),
    order: SortOrder = Query(default=SortOrder.DESC),
) -> PaginatedReadingsOut:
    """Return paginated historical readings for one device."""

    try:
        query = ReadingsQueryParams.model_validate(
            {
                "from": recorded_from,
                "to": recorded_to,
                "parameter": parameter,
                "limit": limit,
                "offset": offset,
                "order": order,
            }
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc

    await _ensure_device_exists(database, device_id)

    page_limit = _resolve_page_limit(
        query.limit,
        settings.readings_default_limit,
        settings.readings_max_limit,
    )

    total = await database.count_readings(
        device_id,
        recorded_from=query.recorded_from,
        recorded_to=query.recorded_to,
        parameter=query.parameter,
    )
    rows = await database.list_readings(
        device_id,
        recorded_from=query.recorded_from,
        recorded_to=query.recorded_to,
        parameter=query.parameter,
        order=query.order.value,
        limit=page_limit,
        offset=query.offset,
    )
    return PaginatedReadingsOut(
        items=[_reading_to_out(row) for row in rows],
        limit=page_limit,
        offset=query.offset,
        total=total,
    )


@router.get("/latest", response_model=list[ReadingOut])
async def latest_readings(
    device_id: str,
    database: DatabaseDep,
    parameter: str | None = Query(default=None),
) -> list[ReadingOut]:
    """Return the latest reading per parameter for one device."""

    await _ensure_device_exists(database, device_id)

    rows = await database.list_latest_readings(device_id, parameter=parameter)
    if not rows:
        raise reading_not_found(device_id, parameter)

    return [_reading_to_out(row) for row in rows]
