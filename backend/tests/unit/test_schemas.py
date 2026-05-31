"""Unit tests for API schema models."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from owp_backend.schemas import (
    DeviceOut,
    HealthResponse,
    LocationOut,
    PaginatedResponse,
    ReadingsQueryParams,
    SortOrder,
)


@pytest.mark.unit
def test_location_out_validates_ranges() -> None:
    with pytest.raises(ValidationError):
        LocationOut(lat=91.0, lon=0.0)


@pytest.mark.unit
def test_paginated_response_generic() -> None:
    page = PaginatedResponse[HealthResponse](
        items=[HealthResponse(status="ok")],
        limit=10,
        offset=0,
        total=1,
    )
    assert page.items[0].status == "ok"
    assert page.total == 1


@pytest.mark.unit
def test_health_response_forbids_extra_fields() -> None:
    with pytest.raises(ValidationError):
        HealthResponse(status="ok", extra="nope")  # type: ignore[call-arg]


@pytest.mark.unit
def test_device_out_null_location() -> None:
    now = datetime(2026, 5, 24, 19, 0, 0, tzinfo=timezone.utc)
    device = DeviceOut(
        device_id="owp-0001",
        first_seen_at=now,
        last_seen_at=now,
        firmware_version=None,
        location=None,
    )
    assert device.location is None


@pytest.mark.unit
def test_readings_query_rejects_invalid_range() -> None:
    start = datetime(2026, 5, 25, tzinfo=timezone.utc)
    end = datetime(2026, 5, 24, tzinfo=timezone.utc)
    with pytest.raises(ValidationError):
        ReadingsQueryParams.model_validate(
            {"from": start.isoformat(), "to": end.isoformat()}
        )


@pytest.mark.unit
def test_sort_order_values() -> None:
    assert SortOrder.DESC.value == "desc"


