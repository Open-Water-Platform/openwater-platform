"""Unit tests for API schema models."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from owp_backend.schemas import HealthResponse, LocationOut, PaginatedResponse


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
