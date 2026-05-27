"""Shared pytest fixtures for the ingestion test suite.

Fixtures live here rather than in per-module conftests so the same
sample ``ReadingEvent`` and test-friendly ``Settings`` are reused across
unit and (future) integration tests.

Defaults chosen here are *test* defaults, not production defaults. In
particular, retry counts and backoff delays are tiny so retry tests
finish in milliseconds.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from owp_ingestion.config import Settings
from owp_ingestion.models import Location, Reading, ReadingEvent


@pytest.fixture
def test_settings() -> Settings:
    """A ``Settings`` instance suitable for fast in-process tests.

    Required fields (``mqtt_host``, ``database_url``) get dummy values
    so the model validates without env vars present. Retry knobs are
    set very small so the retry tests in ``test_db.py`` finish quickly
    even if a sleep slips past mocking.
    """

    return Settings(
        mqtt_host="test-broker",
        database_url="postgresql://test:test@127.0.0.1:5432/test",
        db_write_max_attempts=3,
        db_write_initial_delay=0.01,
        db_write_max_delay=0.04,
        reconnect_initial_delay=0.01,
        reconnect_max_delay=0.04,
    )


@pytest.fixture
def sample_reading() -> Reading:
    """One representative reading. Used as a building block."""

    return Reading(parameter="temperature", value=21.5, unit="C")


@pytest.fixture
def sample_reading_event(sample_reading: Reading) -> ReadingEvent:
    """A fully-populated valid ``ReadingEvent`` with optional fields set."""

    return ReadingEvent(
        device_id="owp-test-0001",
        timestamp=datetime(2026, 5, 24, 19, 22, 30, tzinfo=timezone.utc),
        firmware_version="0.1.0",
        location=Location(lat=12.34, lon=56.78),
        readings=[
            sample_reading,
            Reading(parameter="ph", value=7.2, unit="pH"),
        ],
    )


@pytest.fixture
def sample_reading_event_minimal(sample_reading: Reading) -> ReadingEvent:
    """A minimal valid event: only required fields, one reading.

    Pinning this shape protects the documented contract that
    ``firmware_version`` and ``location`` are optional.
    """

    return ReadingEvent(
        device_id="owp-test-0002",
        timestamp=datetime(2026, 5, 24, 19, 22, 30, tzinfo=timezone.utc),
        readings=[sample_reading],
    )
