"""Unit tests for HTTP routes."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from owp_backend.db import Database, DeviceRow
from owp_backend.routes.devices import router as devices_router
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


def _sample_device_row() -> DeviceRow:
    now = datetime(2026, 5, 24, 19, 0, 0, tzinfo=timezone.utc)
    return DeviceRow(
        device_id="owp-0001",
        first_seen_at=now,
        last_seen_at=now,
        firmware_version="0.1.0",
        location_lat=12.34,
        location_lon=56.78,
    )


def _build_devices_app(database: Database) -> FastAPI:
    app = FastAPI()
    app.state.database = database
    app.include_router(devices_router)
    return app


@pytest.mark.unit
async def test_list_devices_returns_paginated_payload(test_settings) -> None:
    database = Database(test_settings)
    database.count_devices = AsyncMock(return_value=1)
    database.list_devices = AsyncMock(return_value=[_sample_device_row()])
    app = _build_devices_app(database)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.get("/api/v1/devices")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["device_id"] == "owp-0001"


@pytest.mark.unit
async def test_get_device_returns_404_when_missing(test_settings) -> None:
    database = Database(test_settings)
    database.get_device = AsyncMock(return_value=None)
    app = _build_devices_app(database)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.get("/api/v1/devices/missing")

    assert response.status_code == 404

