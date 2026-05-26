"""Unit tests for the database write layer.

These tests pin the architecture's "no silent data loss" rule from the
database module docstring: transient errors retry with exponential
backoff up to ``db_write_max_attempts``; exhaustion raises
``WriteFailedError`` so the MQTT subscriber can withhold the ack and
the broker redelivers; non-retryable errors propagate immediately so
programming bugs surface in logs instead of being silently retried
forever.

The real asyncpg pool is replaced with ``AsyncMock`` plumbing so the
suite never touches a database. ``asyncio.sleep`` is also patched so
exponential-backoff sequences are verified by inspecting call args
rather than by actually waiting.
"""

from __future__ import annotations

from typing import Final
from unittest.mock import AsyncMock, MagicMock

import asyncpg
import pytest

from owp_ingestion.config import Settings
from owp_ingestion.db import Database, WriteFailedError
from owp_ingestion.models import ReadingEvent


pytestmark = pytest.mark.unit


_DEVICE_UPSERT_ARG_COUNT: Final[int] = 6
"""SQL plus device_id, timestamp, firmware_version, lat, lon."""


def _make_pool() -> tuple[MagicMock, AsyncMock]:
    """Construct a mock asyncpg pool + connection pair.

    Returns ``(pool, conn)``. The pool is wired so that

        async with pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute(...)
                await conn.executemany(...)

    works without any real database. ``pool.acquire()`` and
    ``conn.transaction()`` are sync callables (matching asyncpg's real
    surface) that return async context managers.
    """

    conn = AsyncMock()
    conn.execute = AsyncMock(return_value=None)
    conn.executemany = AsyncMock(return_value=None)

    tx_cm = AsyncMock()
    tx_cm.__aenter__ = AsyncMock(return_value=None)
    tx_cm.__aexit__ = AsyncMock(return_value=None)
    conn.transaction = MagicMock(return_value=tx_cm)

    acquire_cm = AsyncMock()
    acquire_cm.__aenter__ = AsyncMock(return_value=conn)
    acquire_cm.__aexit__ = AsyncMock(return_value=None)

    pool = MagicMock()
    pool.acquire = MagicMock(return_value=acquire_cm)
    pool.close = AsyncMock()

    return pool, conn


@pytest.fixture
def mock_pool() -> tuple[MagicMock, AsyncMock]:
    return _make_pool()


@pytest.fixture
def patched_create_pool(
    mocker: "pytest_mock.MockerFixture",
    mock_pool: tuple[MagicMock, AsyncMock],
) -> tuple[AsyncMock, MagicMock, AsyncMock]:
    """Patch ``asyncpg.create_pool`` to return our mock pool.

    Returns ``(create_pool_mock, pool, conn)`` so a test can both assert
    on calls to ``create_pool`` and drive the underlying connection.
    """

    pool, conn = mock_pool
    create_pool = mocker.patch(
        "owp_ingestion.db.asyncpg.create_pool",
        new=AsyncMock(return_value=pool),
    )
    return create_pool, pool, conn


@pytest.fixture
def no_sleep(mocker: "pytest_mock.MockerFixture") -> AsyncMock:
    """Replace ``asyncio.sleep`` in db.py so retry tests don't actually
    wait. Returns the mock so backoff sequences can be asserted."""

    return mocker.patch(
        "owp_ingestion.db.asyncio.sleep", new=AsyncMock(return_value=None)
    )


class TestConnectClose:
    """Pool lifecycle is idempotent in both directions."""

    async def test_connect_opens_the_pool(
        self,
        test_settings: Settings,
        patched_create_pool: tuple[AsyncMock, MagicMock, AsyncMock],
    ) -> None:
        create_pool, _pool, _conn = patched_create_pool
        db = Database(test_settings)

        await db.connect()

        create_pool.assert_awaited_once()
        kwargs = create_pool.call_args.kwargs
        assert kwargs["dsn"] == test_settings.database_url
        assert kwargs["min_size"] == test_settings.db_pool_min_size
        assert kwargs["max_size"] == test_settings.db_pool_max_size

    async def test_connect_is_idempotent(
        self,
        test_settings: Settings,
        patched_create_pool: tuple[AsyncMock, MagicMock, AsyncMock],
    ) -> None:
        create_pool, _pool, _conn = patched_create_pool
        db = Database(test_settings)

        await db.connect()
        await db.connect()

        create_pool.assert_awaited_once()

    async def test_close_is_safe_before_connect(
        self, test_settings: Settings
    ) -> None:
        db = Database(test_settings)

        await db.close()

    async def test_close_is_idempotent(
        self,
        test_settings: Settings,
        patched_create_pool: tuple[AsyncMock, MagicMock, AsyncMock],
    ) -> None:
        _create_pool, pool, _conn = patched_create_pool
        db = Database(test_settings)

        await db.connect()
        await db.close()
        await db.close()

        pool.close.assert_awaited_once()


class TestWriteEventHappyPath:
    """A successful write upserts the device and inserts each reading."""

    async def test_write_event_invokes_upsert_and_insert(
        self,
        test_settings: Settings,
        patched_create_pool: tuple[AsyncMock, MagicMock, AsyncMock],
        sample_reading_event: ReadingEvent,
    ) -> None:
        _create_pool, _pool, conn = patched_create_pool
        db = Database(test_settings)
        await db.connect()

        await db.write_event(sample_reading_event)

        conn.execute.assert_awaited_once()
        execute_args = conn.execute.call_args.args
        assert len(execute_args) == _DEVICE_UPSERT_ARG_COUNT
        assert execute_args[1] == sample_reading_event.device_id
        assert execute_args[2] == sample_reading_event.timestamp
        assert execute_args[3] == sample_reading_event.firmware_version
        assert sample_reading_event.location is not None
        assert execute_args[4] == sample_reading_event.location.lat
        assert execute_args[5] == sample_reading_event.location.lon

    async def test_executemany_gets_one_tuple_per_reading(
        self,
        test_settings: Settings,
        patched_create_pool: tuple[AsyncMock, MagicMock, AsyncMock],
        sample_reading_event: ReadingEvent,
    ) -> None:
        """Idempotency on the success path: each reading becomes a row
        whose composite primary key makes redelivery a no-op."""

        _create_pool, _pool, conn = patched_create_pool
        db = Database(test_settings)
        await db.connect()

        await db.write_event(sample_reading_event)

        conn.executemany.assert_awaited_once()
        rows = conn.executemany.call_args.args[1]
        assert len(rows) == len(sample_reading_event.readings)
        for row, reading in zip(rows, sample_reading_event.readings):
            assert row == (
                sample_reading_event.device_id,
                sample_reading_event.timestamp,
                reading.parameter,
                reading.value,
                reading.unit,
            )

    async def test_missing_location_passes_nulls(
        self,
        test_settings: Settings,
        patched_create_pool: tuple[AsyncMock, MagicMock, AsyncMock],
        sample_reading_event_minimal: ReadingEvent,
    ) -> None:
        """When an event omits ``location``, lat/lon become SQL NULL via
        the ``COALESCE`` upsert rule, preserving any existing location."""

        _create_pool, _pool, conn = patched_create_pool
        db = Database(test_settings)
        await db.connect()

        await db.write_event(sample_reading_event_minimal)

        execute_args = conn.execute.call_args.args
        assert execute_args[4] is None
        assert execute_args[5] is None

    async def test_write_event_without_connect_raises_runtime_error(
        self, test_settings: Settings, sample_reading_event: ReadingEvent
    ) -> None:
        """Catches the easy mistake of forgetting ``await db.connect()``
        before sending traffic at the writer."""

        db = Database(test_settings)

        with pytest.raises(RuntimeError):
            await db.write_event(sample_reading_event)


class TestWriteEventRetry:
    """Transient connection errors retry; permanent errors propagate."""

    async def test_succeeds_on_second_attempt_after_transient_error(
        self,
        test_settings: Settings,
        patched_create_pool: tuple[AsyncMock, MagicMock, AsyncMock],
        no_sleep: AsyncMock,
        sample_reading_event: ReadingEvent,
    ) -> None:
        _create_pool, _pool, conn = patched_create_pool
        conn.execute.side_effect = [
            asyncpg.PostgresConnectionError("broker side hiccup"),
            None,
        ]
        db = Database(test_settings)
        await db.connect()

        await db.write_event(sample_reading_event)

        assert conn.execute.await_count == 2
        no_sleep.assert_awaited_once_with(test_settings.db_write_initial_delay)

    @pytest.mark.parametrize(
        "exc",
        [
            asyncpg.PostgresConnectionError("conn dropped"),
            asyncpg.exceptions.InterfaceError("pool gone"),
            ConnectionError("network blip"),
            OSError("dns failure"),
            TimeoutError("query took too long"),
        ],
    )
    async def test_retries_each_retryable_exception_type(
        self,
        test_settings: Settings,
        patched_create_pool: tuple[AsyncMock, MagicMock, AsyncMock],
        no_sleep: AsyncMock,
        sample_reading_event: ReadingEvent,
        exc: BaseException,
    ) -> None:
        """Pin the full retryable set so a future code change that
        narrows it has to update this test as a deliberate decision."""

        _create_pool, _pool, conn = patched_create_pool
        conn.execute.side_effect = [exc, None]
        db = Database(test_settings)
        await db.connect()

        await db.write_event(sample_reading_event)

        assert conn.execute.await_count == 2

    async def test_exhausts_attempts_and_raises_write_failed_error(
        self,
        test_settings: Settings,
        patched_create_pool: tuple[AsyncMock, MagicMock, AsyncMock],
        no_sleep: AsyncMock,
        sample_reading_event: ReadingEvent,
    ) -> None:
        """The whole point of the wrapper: after ``max_attempts``
        failures, raise a typed error so the MQTT layer can withhold
        the ack and let the broker redeliver later."""

        _create_pool, _pool, conn = patched_create_pool
        conn.execute.side_effect = asyncpg.PostgresConnectionError(
            "db down"
        )
        db = Database(test_settings)
        await db.connect()

        with pytest.raises(WriteFailedError):
            await db.write_event(sample_reading_event)

        assert conn.execute.await_count == test_settings.db_write_max_attempts
        # sleep is called between attempts: max_attempts - 1 sleeps total.
        assert no_sleep.await_count == test_settings.db_write_max_attempts - 1

    async def test_backoff_doubles_and_caps_at_max_delay(
        self,
        test_settings: Settings,
        patched_create_pool: tuple[AsyncMock, MagicMock, AsyncMock],
        no_sleep: AsyncMock,
        sample_reading_event: ReadingEvent,
    ) -> None:
        """Verifies the exponential backoff sequence and the
        ``db_write_max_delay`` cap with a 4-attempt scenario."""

        bigger = test_settings.model_copy(
            update={
                "db_write_max_attempts": 4,
                "db_write_initial_delay": 0.01,
                "db_write_max_delay": 0.03,
            }
        )
        _create_pool, _pool, conn = patched_create_pool
        conn.execute.side_effect = asyncpg.PostgresConnectionError("down")
        db = Database(bigger)
        await db.connect()

        with pytest.raises(WriteFailedError):
            await db.write_event(sample_reading_event)

        delays = [call.args[0] for call in no_sleep.await_args_list]
        # 0.01 -> 0.02 -> min(0.04, 0.03) = 0.03
        assert delays == pytest.approx([0.01, 0.02, 0.03])

    async def test_non_retryable_exception_propagates_immediately(
        self,
        test_settings: Settings,
        patched_create_pool: tuple[AsyncMock, MagicMock, AsyncMock],
        no_sleep: AsyncMock,
        sample_reading_event: ReadingEvent,
    ) -> None:
        """Programming errors like a syntax error in our SQL must
        surface fast and loud, not be hidden by silent retries."""

        _create_pool, _pool, conn = patched_create_pool
        conn.execute.side_effect = asyncpg.exceptions.PostgresSyntaxError(
            "boom"
        )
        db = Database(test_settings)
        await db.connect()

        with pytest.raises(asyncpg.exceptions.PostgresSyntaxError):
            await db.write_event(sample_reading_event)

        assert conn.execute.await_count == 1
        no_sleep.assert_not_awaited()

    async def test_write_failed_error_chains_the_root_cause(
        self,
        test_settings: Settings,
        patched_create_pool: tuple[AsyncMock, MagicMock, AsyncMock],
        no_sleep: AsyncMock,
        sample_reading_event: ReadingEvent,
    ) -> None:
        """Operators reading logs need the underlying asyncpg error,
        not just ``WriteFailedError: after N attempts``."""

        root_cause = asyncpg.PostgresConnectionError("upstream gone")
        _create_pool, _pool, conn = patched_create_pool
        conn.execute.side_effect = root_cause
        db = Database(test_settings)
        await db.connect()

        with pytest.raises(WriteFailedError) as exc_info:
            await db.write_event(sample_reading_event)

        assert exc_info.value.__cause__ is root_cause
