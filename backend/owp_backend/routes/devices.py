"""Device routes."""

from __future__ import annotations

from fastapi import APIRouter, Query

from owp_backend.db import DeviceRow
from owp_backend.dependencies import DatabaseDep, SettingsDep
from owp_backend.errors import device_not_found
from owp_backend.schemas import DeviceOut, LocationOut, PaginatedDevicesOut

router = APIRouter(prefix="/api/v1/devices", tags=["devices"])


def _device_to_out(row: DeviceRow) -> DeviceOut:
    location = None
    if row.location_lat is not None and row.location_lon is not None:
        location = LocationOut(lat=row.location_lat, lon=row.location_lon)
    return DeviceOut(
        device_id=row.device_id,
        first_seen_at=row.first_seen_at,
        last_seen_at=row.last_seen_at,
        firmware_version=row.firmware_version,
        location=location,
    )


@router.get("", response_model=PaginatedDevicesOut)
async def list_devices(
    database: DatabaseDep,
    settings: SettingsDep,
    limit: int | None = Query(default=None, ge=1),
    offset: int = Query(default=0, ge=0),
) -> PaginatedDevicesOut:
    """Return a paginated list of registered devices."""

    page_limit = limit or settings.devices_default_limit
    if page_limit > settings.devices_max_limit:
        page_limit = settings.devices_max_limit

    total = await database.count_devices()
    rows = await database.list_devices(limit=page_limit, offset=offset)
    return PaginatedDevicesOut(
        items=[_device_to_out(row) for row in rows],
        limit=page_limit,
        offset=offset,
        total=total,
    )


@router.get("/{device_id}", response_model=DeviceOut)
async def get_device(device_id: str, database: DatabaseDep) -> DeviceOut:
    """Return metadata for a single device."""

    row = await database.get_device(device_id)
    if row is None:
        raise device_not_found(device_id)
    return _device_to_out(row)
