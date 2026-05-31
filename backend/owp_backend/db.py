"""Database access layer for the backend service.

Owns the asyncpg connection pool and read-only queries against ``devices``
and ``readings``. The backend never writes to these tables; ingestion owns
writes per the architecture table-ownership rules.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Final

import asyncpg

from .config import Settings

logger = logging.getLogger(__name__)

_PING_SQL: Final[str] = "SELECT 1"


@dataclass(frozen=True, slots=True)
class DeviceRow:
    """One row from the ``devices`` table."""

    device_id: str
    first_seen_at: datetime
    last_seen_at: datetime
    firmware_version: str | None
    location_lat: float | None
    location_lon: float | None


@dataclass(frozen=True, slots=True)
class ReadingRow:
    """One row from the ``readings`` table."""

    device_id: str
    recorded_at: datetime
    parameter: str
    value: float
    unit: str


class Database:
    """Async wrapper around an asyncpg pool with read-only queries."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._pool: asyncpg.Pool | None = None

    async def connect(self) -> None:
        """Open the connection pool. Idempotent."""

        if self._pool is not None:
            return

        logger.info(
            "opening postgres pool min=%d max=%d command_timeout=%.1fs",
            self._settings.db_pool_min_size,
            self._settings.db_pool_max_size,
            self._settings.db_command_timeout,
        )
        self._pool = await asyncpg.create_pool(
            dsn=self._settings.database_url,
            min_size=self._settings.db_pool_min_size,
            max_size=self._settings.db_pool_max_size,
            command_timeout=self._settings.db_command_timeout,
        )
        logger.info("postgres pool ready")

    async def close(self) -> None:
        """Close the pool. Safe to call multiple times."""

        if self._pool is None:
            return
        await self._pool.close()
        self._pool = None
        logger.info("postgres pool closed")

    async def ping(self) -> None:
        """Verify the database accepts queries. Used by readiness checks."""

        pool = self._require_pool()
        async with pool.acquire() as conn:
            await conn.fetchval(_PING_SQL)

    def _require_pool(self) -> asyncpg.Pool:
        if self._pool is None:
            raise RuntimeError("Database.connect() must be called before queries")
        return self._pool
