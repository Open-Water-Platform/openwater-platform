"""Unit tests for the database pool lifecycle."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from owp_backend.config import Settings
from owp_backend.db import Database


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
async def test_ping_runs_select_one(test_settings: Settings) -> None:
    database = Database(test_settings)
    mock_conn = AsyncMock()
    mock_conn.fetchval = AsyncMock(return_value=1)
    mock_pool = MagicMock()
    mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=False)
    database._pool = mock_pool  # noqa: SLF001

    await database.ping()

    mock_conn.fetchval.assert_awaited_once_with("SELECT 1")


@pytest.mark.unit
async def test_ping_requires_connected_pool(test_settings: Settings) -> None:
    database = Database(test_settings)

    with pytest.raises(RuntimeError, match="connect"):
        await database.ping()
