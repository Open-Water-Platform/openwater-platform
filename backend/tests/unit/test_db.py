"""Unit tests for the database pool lifecycle."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from owp_backend.config import Settings
from owp_backend.db import Database, DatabaseUnavailableError, DeviceRow


@pytest.mark.unit
async def test_connect_opens_pool_once(test_settings: Settings) -> None:
    database = Database(test_settings)
    mock_pool = AsyncMock()

    with patch("owp_backend.db.asyncpg.create_pool", AsyncMock(return_value=mock_pool)) as create_pool:
        await database.connect()
        await database.connect()

    create_pool.assert_awaited_once()


@pytest.mark.unit
async def test_close_is_idempotent(test_settings: Settings) -> None:
    database = Database(test_settings)
    mock_pool = AsyncMock()

    with patch("owp_backend.db.asyncpg.create_pool", AsyncMock(return_value=mock_pool)):
        await database.connect()

    await database.close()
    await database.close()

    mock_pool.close.assert_awaited_once()


@pytest.mark.unit
async def test_connect_raises_when_pool_unavailable(test_settings: Settings) -> None:
    database = Database(test_settings)

    with patch(
        "owp_backend.db.asyncpg.create_pool",
        AsyncMock(side_effect=ConnectionError("connection refused")),
    ):
        with pytest.raises(DatabaseUnavailableError, match="connection refused"):
            await database.connect()


@pytest.mark.unit
async def test_ping_lazy_connects(test_settings: Settings) -> None:
    database = Database(test_settings)
    mock_conn = AsyncMock()
    mock_conn.fetchval = AsyncMock(return_value=1)
    mock_pool = MagicMock()
    mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=False)

    with patch(
        "owp_backend.db.asyncpg.create_pool",
        AsyncMock(return_value=mock_pool),
    ) as create_pool:
        await database.ping()

    create_pool.assert_awaited_once()
    mock_conn.fetchval.assert_awaited_once_with("SELECT 1")


def _sample_device_record() -> dict[str, object]:
    now = datetime(2026, 5, 24, 19, 0, 0, tzinfo=timezone.utc)
    return {
        "device_id": "owp-0001",
        "first_seen_at": now,
        "last_seen_at": now,
        "firmware_version": "0.1.0",
        "location_lat": 12.34,
        "location_lon": 56.78,
    }


@pytest.mark.unit
async def test_list_devices_maps_rows(test_settings: Settings) -> None:
    database = Database(test_settings)
    mock_conn = AsyncMock()
    mock_conn.fetch = AsyncMock(return_value=[_sample_device_record()])
    mock_pool = MagicMock()
    mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=False)
    database._pool = mock_pool  # noqa: SLF001

    devices = await database.list_devices(limit=10, offset=0)

    assert len(devices) == 1
    assert devices[0].device_id == "owp-0001"
    mock_conn.fetch.assert_awaited_once()


@pytest.mark.unit
async def test_get_device_returns_none_when_missing(test_settings: Settings) -> None:
    database = Database(test_settings)
    mock_conn = AsyncMock()
    mock_conn.fetchrow = AsyncMock(return_value=None)
    mock_pool = MagicMock()
    mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=False)
    database._pool = mock_pool  # noqa: SLF001

    device = await database.get_device("missing")

    assert device is None


@pytest.mark.unit
async def test_device_exists(test_settings: Settings) -> None:
    database = Database(test_settings)
    mock_conn = AsyncMock()
    mock_conn.fetchval = AsyncMock(return_value=1)
    mock_pool = MagicMock()
    mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=False)
    database._pool = mock_pool  # noqa: SLF001

    assert await database.device_exists("owp-0001") is True


@pytest.mark.unit
async def test_list_readings_uses_order_clause(test_settings: Settings) -> None:
    database = Database(test_settings)
    mock_conn = AsyncMock()
    mock_conn.fetch = AsyncMock(return_value=[])
    mock_pool = MagicMock()
    mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=False)
    database._pool = mock_pool  # noqa: SLF001

    await database.list_readings(
        "owp-0001",
        recorded_from=None,
        recorded_to=None,
        parameter=None,
        order="desc",
        limit=10,
        offset=0,
    )

    sql_used = mock_conn.fetch.await_args.args[0]
    assert "ORDER BY recorded_at DESC" in sql_used


