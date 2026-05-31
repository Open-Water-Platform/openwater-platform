"""Pydantic models for HTTP API request and response bodies."""

from __future__ import annotations

from datetime import datetime
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

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
