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

_LIST_DEVICES_SQL: Final[str] = """
    SELECT device_id, first_seen_at, last_seen_at,
           firmware_version, location_lat, location_lon
    FROM devices
    ORDER BY last_seen_at DESC
    LIMIT $1 OFFSET $2
"""

_COUNT_DEVICES_SQL: Final[str] = "SELECT COUNT(*) FROM devices"

_GET_DEVICE_SQL: Final[str] = """
    SELECT device_id, first_seen_at, last_seen_at,
           firmware_version, location_lat, location_lon
    FROM devices
    WHERE device_id = $1
"""

_DEVICE_EXISTS_SQL: Final[str] = "SELECT 1 FROM devices WHERE device_id = $1"

_LIST_READINGS_SQL: Final[str] = """
    SELECT device_id, recorded_at, parameter, value, unit
    FROM readings
    WHERE device_id = $1
      AND ($2::timestamptz IS NULL OR recorded_at >= $2)
      AND ($3::timestamptz IS NULL OR recorded_at <= $3)
      AND ($4::text IS NULL OR parameter = $4)
    ORDER BY recorded_at {order}
    LIMIT $5 OFFSET $6
"""

_COUNT_READINGS_SQL: Final[str] = """
    SELECT COUNT(*)
    FROM readings
    WHERE device_id = $1
      AND ($2::timestamptz IS NULL OR recorded_at >= $2)
      AND ($3::timestamptz IS NULL OR recorded_at <= $3)
      AND ($4::text IS NULL OR parameter = $4)
"""

_LATEST_READINGS_SQL: Final[str] = """
    SELECT DISTINCT ON (parameter)
           device_id, recorded_at, parameter, value, unit
    FROM readings
    WHERE device_id = $1
      AND ($2::text IS NULL OR parameter = $2)
    ORDER BY parameter, recorded_at DESC
"""


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

    async def count_devices(self) -> int:
        """Return the total number of registered devices."""

        pool = self._require_pool()
        async with pool.acquire() as conn:
            total = await conn.fetchval(_COUNT_DEVICES_SQL)
        return int(total)

    async def list_devices(self, *, limit: int, offset: int) -> list[DeviceRow]:
        """Return a page of devices ordered by most recently seen."""

        pool = self._require_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(_LIST_DEVICES_SQL, limit, offset)
        return [_device_row_from_record(row) for row in rows]

    async def get_device(self, device_id: str) -> DeviceRow | None:
        """Return one device by id, or ``None`` if not registered."""

        pool = self._require_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(_GET_DEVICE_SQL, device_id)
        if row is None:
            return None
        return _device_row_from_record(row)

    async def device_exists(self, device_id: str) -> bool:
        """Return whether a device id is registered."""

        pool = self._require_pool()
        async with pool.acquire() as conn:
            value = await conn.fetchval(_DEVICE_EXISTS_SQL, device_id)
        return value is not None

    async def count_readings(
        self,
        device_id: str,
        *,
        recorded_from: datetime | None,
        recorded_to: datetime | None,
        parameter: str | None,
    ) -> int:
        """Return the number of readings matching the filters."""

        pool = self._require_pool()
        async with pool.acquire() as conn:
            total = await conn.fetchval(
                _COUNT_READINGS_SQL,
                device_id,
                recorded_from,
                recorded_to,
                parameter,
            )
        return int(total)

    async def list_readings(
        self,
        device_id: str,
        *,
        recorded_from: datetime | None,
        recorded_to: datetime | None,
        parameter: str | None,
        order: str,
        limit: int,
        offset: int,
    ) -> list[ReadingRow]:
        """Return a page of readings for one device."""

        if order not in {"asc", "desc"}:
            raise ValueError(f"unsupported order: {order}")

        sql = _LIST_READINGS_SQL.format(order=order.upper())
        pool = self._require_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                sql,
                device_id,
                recorded_from,
                recorded_to,
                parameter,
                limit,
                offset,
            )
        return [_reading_row_from_record(row) for row in rows]

    async def list_latest_readings(
        self,
        device_id: str,
        *,
        parameter: str | None,
    ) -> list[ReadingRow]:
        """Return the latest reading per parameter for one device."""

        pool = self._require_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                _LATEST_READINGS_SQL,
                device_id,
                parameter,
            )
        return [_reading_row_from_record(row) for row in rows]

    def _require_pool(self) -> asyncpg.Pool:
        if self._pool is None:
            raise RuntimeError("Database.connect() must be called before queries")
        return self._pool


def _device_row_from_record(row: asyncpg.Record) -> DeviceRow:
    return DeviceRow(
        device_id=row["device_id"],
        first_seen_at=row["first_seen_at"],
        last_seen_at=row["last_seen_at"],
        firmware_version=row["firmware_version"],
        location_lat=row["location_lat"],
        location_lon=row["location_lon"],
    )


def _reading_row_from_record(row: asyncpg.Record) -> ReadingRow:
    return ReadingRow(
        device_id=row["device_id"],
        recorded_at=row["recorded_at"],
        parameter=row["parameter"],
        value=row["value"],
        unit=row["unit"],
    )
