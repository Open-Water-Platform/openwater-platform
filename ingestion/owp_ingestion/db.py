"""Database access layer for the ingestion service.

Owns the asyncpg connection pool and the only two write paths ingestion
needs: upserting a row in ``devices`` and inserting one or more rows in
``readings`` for a single :class:`ReadingEvent`. Both happen atomically
inside one transaction per event.

Two failure layers compose around these writes:

* **In-process retry** (this module). Transient connection errors and
  timeouts are caught and the write is retried with exponential backoff
  up to ``db_write_max_attempts``. Most short-lived DB blips never reach
  the second layer.
* **Manual MQTT ack** (in :mod:`.mqtt_client`). If retries are exhausted,
  the write raises :class:`WriteFailedError`; the subscriber loop then
  declines to ACK the originating MQTT message, so the broker redelivers
  it on the next reconnect. This is what makes the architecture's
  'does not silently drop data' rule hold across service crashes.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Final

import asyncpg

from .config import Settings
from .models import ReadingEvent

logger = logging.getLogger(__name__)

_DEVICE_UPSERT_SQL: Final[str] = """
    INSERT INTO devices (
        device_id, first_seen_at, last_seen_at,
        firmware_version, location_lat, location_lon
    )
    VALUES ($1, $2, $2, $3, $4, $5)
    ON CONFLICT (device_id) DO UPDATE SET
        last_seen_at     = EXCLUDED.last_seen_at,
        firmware_version = COALESCE(EXCLUDED.firmware_version, devices.firmware_version),
        location_lat     = COALESCE(EXCLUDED.location_lat,     devices.location_lat),
        location_lon     = COALESCE(EXCLUDED.location_lon,     devices.location_lon)
"""

_READING_INSERT_SQL: Final[str] = """
    INSERT INTO readings (device_id, recorded_at, parameter, value, unit)
    VALUES ($1, $2, $3, $4, $5)
    ON CONFLICT (device_id, recorded_at, parameter) DO NOTHING
"""

_RETRYABLE_EXCEPTIONS: Final[tuple[type[BaseException], ...]] = (
    asyncpg.PostgresConnectionError,
    asyncpg.exceptions.InterfaceError,
    ConnectionError,
    OSError,
    TimeoutError,
    asyncio.TimeoutError,
)
"""Errors the in-process retry wrapper will catch and retry.

Anything else (programming errors, constraint violations, syntax errors)
propagates immediately so it surfaces at startup or in logs instead of
being silently retried forever.
"""


class WriteFailedError(Exception):
    """Raised when all in-process retry attempts to write an event fail.

    The MQTT subscriber treats this as the signal to *not* acknowledge
    the originating message so the broker redelivers it later.
    """


class Database:
    """Async wrapper around an asyncpg pool with idempotent event writes."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._pool: asyncpg.Pool | None = None

    async def connect(self) -> None:
        """Open the connection pool.

        Idempotent: calling :meth:`connect` again on an already-connected
        instance is a no-op. Connection establishment failures propagate;
        the caller (``main.py``) decides whether to retry startup.
        """

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

    async def write_event(self, event: ReadingEvent) -> None:
        """Persist a validated event with in-process retry.

        Raises :class:`WriteFailedError` once retry budget is exhausted.
        """

        attempt = 0
        delay = self._settings.db_write_initial_delay
        max_attempts = self._settings.db_write_max_attempts

        while True:
            attempt += 1
            try:
                await self._write_once(event)
            except _RETRYABLE_EXCEPTIONS as exc:
                if attempt >= max_attempts:
                    logger.error(
                        "db write giving up after %d attempts device_id=%s timestamp=%s error=%s",
                        attempt,
                        event.device_id,
                        event.timestamp.isoformat(),
                        exc,
                    )
                    raise WriteFailedError(
                        f"after {attempt} attempts: {exc!s}"
                    ) from exc
                logger.warning(
                    "db write attempt %d/%d failed device_id=%s error=%s retry_in=%.1fs",
                    attempt,
                    max_attempts,
                    event.device_id,
                    exc,
                    delay,
                )
                await asyncio.sleep(delay)
                delay = min(delay * 2, self._settings.db_write_max_delay)
                continue

            if attempt > 1:
                logger.info(
                    "db write succeeded on attempt %d device_id=%s",
                    attempt,
                    event.device_id,
                )
            return

    async def _write_once(self, event: ReadingEvent) -> None:
        """Single best-effort write inside one transaction."""

        if self._pool is None:
            raise RuntimeError("Database.connect() must be called before write_event")

        async with self._pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute(
                    _DEVICE_UPSERT_SQL,
                    event.device_id,
                    event.timestamp,
                    event.firmware_version,
                    event.location.lat if event.location else None,
                    event.location.lon if event.location else None,
                )
                await conn.executemany(
                    _READING_INSERT_SQL,
                    [
                        (
                            event.device_id,
                            event.timestamp,
                            reading.parameter,
                            reading.value,
                            reading.unit,
                        )
                        for reading in event.readings
                    ],
                )
