"""HTTP-layer exception helpers."""

from __future__ import annotations

from fastapi import HTTPException, status


def device_not_found(device_id: str) -> HTTPException:
    """Return a consistent 404 for unknown devices."""

    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Device not found: {device_id}",
    )


def reading_not_found(device_id: str, parameter: str | None = None) -> HTTPException:
    """Return a consistent 404 when no matching readings exist."""

    if parameter is None:
        detail = f"No readings found for device: {device_id}"
    else:
        detail = (
            f"No readings found for device {device_id} "
            f"with parameter: {parameter}"
        )
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)
