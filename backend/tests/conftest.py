"""Shared pytest fixtures for the backend test suite."""

from __future__ import annotations

import pytest

from owp_backend.config import Settings
from owp_backend.dependencies import get_settings


@pytest.fixture(autouse=True)
def _set_required_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure settings can load without a local ``.env`` file."""

    monkeypatch.setenv("OWP_DATABASE_URL", "postgresql://test:test@127.0.0.1:5432/test")
    get_settings.cache_clear()


@pytest.fixture
def test_settings() -> Settings:
    """A ``Settings`` instance suitable for fast in-process tests."""

    return Settings(
        database_url="postgresql://test:test@127.0.0.1:5432/test",
        db_pool_min_size=1,
        db_pool_max_size=2,
        db_command_timeout=1.0,
        readings_default_limit=10,
        readings_max_limit=100,
        devices_default_limit=5,
        devices_max_limit=50,
    )
