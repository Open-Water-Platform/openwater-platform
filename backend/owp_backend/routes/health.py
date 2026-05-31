"""Health check routes."""

from __future__ import annotations

from fastapi import APIRouter, Response, status

from owp_backend.db import DatabaseUnavailableError
from owp_backend.dependencies import DatabaseDep
from owp_backend.schemas import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def liveness() -> HealthResponse:
    """Process liveness probe — does not touch the database."""

    return HealthResponse(status="backend is running")


@router.get("/health/ready", response_model=HealthResponse)
async def readiness(database: DatabaseDep, response: Response) -> HealthResponse:
    """Readiness probe — verifies the database accepts queries."""

    try:
        await database.ping()
    except DatabaseUnavailableError:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return HealthResponse(status="db is unavailable")
    return HealthResponse(status="db is ready")
