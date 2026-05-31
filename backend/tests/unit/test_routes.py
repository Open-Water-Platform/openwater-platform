"""Unit tests for HTTP routes."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from owp_backend.db import Database
from owp_backend.routes.health import router as health_router


def _build_health_app(database: Database) -> FastAPI:
    app = FastAPI()
    app.state.database = database
    app.include_router(health_router)
    return app


@pytest.mark.unit
async def test_liveness_returns_ok(test_settings) -> None:
    database = Database(test_settings)
    app = _build_health_app(database)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.unit
async def test_readiness_returns_ready_when_db_ok(test_settings) -> None:
    database = Database(test_settings)
    database.ping = AsyncMock()
    app = _build_health_app(database)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.get("/health/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ready"}
    database.ping.assert_awaited_once()


@pytest.mark.unit
async def test_readiness_returns_503_when_db_fails(test_settings) -> None:
    database = Database(test_settings)
    database.ping = AsyncMock(side_effect=RuntimeError("db down"))
    app = _build_health_app(database)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.get("/health/ready")

    assert response.status_code == 503
    assert response.json() == {"status": "unavailable"}
