"""Unit tests for HTTP routes."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from httpx import ASGITransport, AsyncClient

from owp_backend.db import Database, DatabaseUnavailableError, DeviceRow, ReadingRow
from owp_backend.routes.devices import router as devices_router
from owp_backend.routes.health import router as health_router
from owp_backend.routes.readings import router as readings_router


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
    assert response.json() == {"status": "backend is running"}


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
    assert response.json() == {"status": "db is ready"}
    database.ping.assert_awaited_once()


@pytest.mark.unit
async def test_readiness_returns_503_when_db_fails(test_settings) -> None:
    database = Database(test_settings)
    database.ping = AsyncMock(side_effect=DatabaseUnavailableError("db down"))
    app = _build_health_app(database)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.get("/health/ready")

    assert response.status_code == 503
    assert response.json() == {"status": "db is unavailable"}


@pytest.mark.unit
async def test_liveness_works_without_database_connection(test_settings) -> None:
    database = Database(test_settings)
    database.ping = AsyncMock(
        side_effect=DatabaseUnavailableError("should not be called")
    )
    app = _build_health_app(database)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.get("/health")

    assert response.status_code == 200
    database.ping.assert_not_called()


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

    @app.exception_handler(DatabaseUnavailableError)
    async def database_unavailable_handler(
        request,
        exc: DatabaseUnavailableError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=503,
            content={"detail": "Database unavailable"},
        )

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


@pytest.mark.unit
async def test_list_devices_returns_503_when_db_unavailable(test_settings) -> None:
    database = Database(test_settings)
    database.count_devices = AsyncMock(
        side_effect=DatabaseUnavailableError("connection refused")
    )
    app = _build_devices_app(database)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.get("/api/v1/devices")

    assert response.status_code == 503
    assert response.json() == {"detail": "Database unavailable"}


def _sample_reading_row() -> ReadingRow:
    now = datetime(2026, 5, 24, 19, 22, 30, tzinfo=timezone.utc)
    return ReadingRow(
        device_id="owp-0001",
        recorded_at=now,
        parameter="temperature",
        value=21.5,
        unit="C",
    )


def _build_readings_app(database: Database) -> FastAPI:
    app = FastAPI()
    app.state.database = database
    app.include_router(readings_router)
    return app


@pytest.mark.unit
async def test_list_readings_returns_paginated_payload(test_settings) -> None:
    database = Database(test_settings)
    database.device_exists = AsyncMock(return_value=True)
    database.count_readings = AsyncMock(return_value=1)
    database.list_readings = AsyncMock(return_value=[_sample_reading_row()])
    app = _build_readings_app(database)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.get("/api/v1/devices/owp-0001/readings")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["parameter"] == "temperature"


@pytest.mark.unit
async def test_list_readings_returns_404_for_unknown_device(test_settings) -> None:
    database = Database(test_settings)
    database.device_exists = AsyncMock(return_value=False)
    app = _build_readings_app(database)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.get("/api/v1/devices/missing/readings")

    assert response.status_code == 404


@pytest.mark.unit
async def test_list_readings_returns_422_for_invalid_range(test_settings) -> None:
    database = Database(test_settings)
    app = _build_readings_app(database)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.get(
            "/api/v1/devices/owp-0001/readings",
            params={
                "from": "2026-05-25T00:00:00Z",
                "to": "2026-05-24T00:00:00Z",
            },
        )

    assert response.status_code == 422


@pytest.mark.unit
async def test_latest_readings_returns_values(test_settings) -> None:
    database = Database(test_settings)
    database.device_exists = AsyncMock(return_value=True)
    database.list_latest_readings = AsyncMock(return_value=[_sample_reading_row()])
    app = _build_readings_app(database)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.get("/api/v1/devices/owp-0001/readings/latest")

    assert response.status_code == 200
    assert response.json()[0]["parameter"] == "temperature"


@pytest.mark.unit
async def test_latest_readings_returns_404_when_empty(test_settings) -> None:
    database = Database(test_settings)
    database.device_exists = AsyncMock(return_value=True)
    database.list_latest_readings = AsyncMock(return_value=[])
    app = _build_readings_app(database)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.get(
            "/api/v1/devices/owp-0001/readings/latest",
            params={"parameter": "temperature"},
        )

    assert response.status_code == 404


