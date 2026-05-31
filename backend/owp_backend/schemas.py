"""Pydantic models for HTTP API request and response bodies."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field, model_validator

ItemT = TypeVar("ItemT")


class LocationOut(BaseModel):
    """Geographic location exposed in API responses."""

    model_config = ConfigDict(extra="forbid")

    lat: float = Field(..., ge=-90.0, le=90.0)
    lon: float = Field(..., ge=-180.0, le=180.0)


class PaginatedResponse(BaseModel, Generic[ItemT]):
    """Common pagination envelope for list endpoints."""

    model_config = ConfigDict(extra="forbid")

    items: list[ItemT]
    limit: int = Field(..., ge=0)
    offset: int = Field(..., ge=0)
    total: int = Field(..., ge=0)


class HealthResponse(BaseModel):
    """Liveness or readiness response body."""

    model_config = ConfigDict(extra="forbid")

    status: str


class DeviceOut(BaseModel):
    """Device metadata exposed by the API."""

    model_config = ConfigDict(extra="forbid")

    device_id: str
    first_seen_at: datetime
    last_seen_at: datetime
    firmware_version: str | None = None
    location: LocationOut | None = None


class PaginatedDevicesOut(PaginatedResponse[DeviceOut]):
    """Paginated list of devices."""


class SortOrder(StrEnum):
    """Allowed sort directions for time-series list endpoints."""

    ASC = "asc"
    DESC = "desc"


class ReadingOut(BaseModel):
    """One sensor reading exposed by the API."""

    model_config = ConfigDict(extra="forbid")

    device_id: str
    recorded_at: datetime
    parameter: str
    value: float
    unit: str


class PaginatedReadingsOut(PaginatedResponse[ReadingOut]):
    """Paginated list of readings."""


class ReadingsQueryParams(BaseModel):
    """Validated query parameters for readings list endpoints."""

    model_config = ConfigDict(extra="forbid")

    recorded_from: datetime | None = Field(default=None, alias="from")
    recorded_to: datetime | None = Field(default=None, alias="to")
    parameter: str | None = None
    limit: int | None = Field(default=None, ge=1)
    offset: int = Field(default=0, ge=0)
    order: SortOrder = SortOrder.DESC

    @model_validator(mode="after")
    def _validate_time_range(self) -> ReadingsQueryParams:
        if (
            self.recorded_from is not None
            and self.recorded_to is not None
            and self.recorded_from > self.recorded_to
        ):
            raise ValueError("'from' must not be after 'to'")
        return self


