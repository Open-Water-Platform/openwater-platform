"""Unit tests for backend configuration."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from owp_backend.config import Settings, load_settings


@pytest.mark.unit
def test_settings_requires_database_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OWP_DATABASE_URL", raising=False)
    with pytest.raises(ValidationError):
        Settings()  # type: ignore[call-arg]


@pytest.mark.unit
def test_settings_defaults(test_settings: Settings) -> None:
    assert test_settings.host == "0.0.0.0"
    assert test_settings.port == 8000
    assert test_settings.log_level == "INFO"
    assert test_settings.readings_default_limit == 10
    assert test_settings.devices_default_limit == 5


@pytest.mark.unit
def test_settings_uses_owp_prefix(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OWP_DATABASE_URL", "postgresql://a:b@localhost/db")
    monkeypatch.setenv("OWP_PORT", "9000")
    settings = load_settings()
    assert settings.database_url == "postgresql://a:b@localhost/db"
    assert settings.port == 9000


@pytest.mark.unit
def test_cors_origins_parsed_to_list(test_settings: Settings) -> None:
    settings = test_settings.model_copy(
        update={"cors_origins": "http://a.test, http://b.test"}
    )
    assert settings.cors_origin_list == ["http://a.test", "http://b.test"]


@pytest.mark.unit
def test_readings_max_limit_must_be_positive() -> None:
    with pytest.raises(ValidationError):
        Settings(
            database_url="postgresql://test:test@127.0.0.1:5432/test",
            readings_max_limit=0,
        )
