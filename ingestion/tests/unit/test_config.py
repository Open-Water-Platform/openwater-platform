"""Unit tests for runtime Settings loading.

The point of these tests is to pin the *operator-facing* contract of
the service: which environment variables are required, which have
defaults, and which constraints fail fast at startup.

The ``_isolated_env`` fixture is autouse so every test starts with no
``OWP_*`` variables in the environment and an empty CWD, regardless of
what the developer happens to have exported locally. Without it, a
stray ``OWP_MQTT_HOST=localhost`` in your shell would silently mask the
"required field is required" tests.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from owp_ingestion.config import Settings, load_settings


pytestmark = pytest.mark.unit


_REQUIRED_ENV = {
    "OWP_MQTT_HOST": "broker.example.com",
    "OWP_DATABASE_URL": "postgresql://owp:owp@127.0.0.1:5432/owp",
}


@pytest.fixture(autouse=True)
def _isolated_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Clear all OWP_* env vars and chdir to an empty tmp dir.

    Pydantic-settings reads ``.env`` from the current working directory,
    so we point the tests at a clean directory to avoid picking up the
    developer's local ingestion/.env file.
    """

    for name in list(_iter_owp_env_names(monkeypatch)):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.chdir(tmp_path)


def _iter_owp_env_names(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Return the names of all OWP_-prefixed env vars currently set.

    Walks ``os.environ`` once so the autouse fixture can wipe whatever
    the developer has exported without hard-coding a list that would
    drift as Settings grows.
    """

    import os

    return [name for name in os.environ if name.startswith("OWP_")]


def _set_required(monkeypatch: pytest.MonkeyPatch) -> None:
    for name, value in _REQUIRED_ENV.items():
        monkeypatch.setenv(name, value)


class TestRequiredFields:
    """``mqtt_host`` and ``database_url`` must come from the operator."""

    def test_no_env_raises_validation_error(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            Settings()

        error_fields = {err["loc"][0] for err in exc_info.value.errors()}
        assert "mqtt_host" in error_fields
        assert "database_url" in error_fields

    def test_load_settings_helper_also_fails_fast(self) -> None:
        """``load_settings()`` is the public entrypoint; verify it
        surfaces the same error rather than swallowing it."""

        with pytest.raises(ValidationError):
            load_settings()

    def test_required_env_vars_satisfy_the_model(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _set_required(monkeypatch)

        settings = Settings()

        assert settings.mqtt_host == "broker.example.com"
        assert (
            settings.database_url
            == "postgresql://owp:owp@127.0.0.1:5432/owp"
        )


class TestDefaults:
    """Optional fields fall back to documented defaults."""

    def test_optional_fields_have_expected_defaults(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _set_required(monkeypatch)

        settings = Settings()

        assert settings.mqtt_port == 1883
        assert settings.mqtt_username is None
        assert settings.mqtt_password is None
        assert settings.mqtt_topic == "owp/v1/devices/+/readings"
        assert settings.mqtt_client_id == "owp-ingestion"
        assert settings.mqtt_qos == 1
        assert settings.reconnect_initial_delay == 1.0
        assert settings.reconnect_max_delay == 30.0
        assert settings.db_pool_min_size == 1
        assert settings.db_pool_max_size == 5
        assert settings.db_command_timeout == 10.0
        assert settings.db_write_max_attempts == 10
        assert settings.db_write_initial_delay == 1.0
        assert settings.db_write_max_delay == 30.0
        assert settings.log_level == "INFO"


class TestEnvVarBinding:
    """OWP_-prefixed env vars override defaults; bare names do not."""

    def test_env_vars_override_defaults(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _set_required(monkeypatch)
        monkeypatch.setenv("OWP_MQTT_PORT", "8883")
        monkeypatch.setenv("OWP_MQTT_USERNAME", "owp")
        monkeypatch.setenv("OWP_LOG_LEVEL", "DEBUG")
        monkeypatch.setenv("OWP_DB_POOL_MAX_SIZE", "20")

        settings = Settings()

        assert settings.mqtt_port == 8883
        assert settings.mqtt_username == "owp"
        assert settings.log_level == "DEBUG"
        assert settings.db_pool_max_size == 20

    def test_string_env_vars_are_coerced_to_numbers(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _set_required(monkeypatch)
        monkeypatch.setenv("OWP_DB_WRITE_INITIAL_DELAY", "0.25")
        monkeypatch.setenv("OWP_DB_WRITE_MAX_ATTEMPTS", "3")

        settings = Settings()

        assert settings.db_write_initial_delay == 0.25
        assert isinstance(settings.db_write_initial_delay, float)
        assert settings.db_write_max_attempts == 3
        assert isinstance(settings.db_write_max_attempts, int)

    def test_unprefixed_env_var_does_not_bind(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """``MQTT_HOST`` without the ``OWP_`` prefix must not leak in;
        we set both to prove the prefix is enforced rather than just
        coincidentally working."""

        monkeypatch.setenv("MQTT_HOST", "should-be-ignored")
        monkeypatch.setenv("DATABASE_URL", "should-be-ignored")

        with pytest.raises(ValidationError):
            Settings()

    def test_unknown_owp_var_is_ignored(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """``extra="ignore"`` means an unknown OWP_FOO doesn't fail the
        model. Useful so an operator's stale env doesn't crash the
        service after a Settings field is removed."""

        _set_required(monkeypatch)
        monkeypatch.setenv("OWP_RETIRED_FLAG", "yes")

        Settings()


class TestValidators:
    """Numeric range constraints fail fast at startup."""

    @pytest.mark.parametrize("port", ["0", "65536", "-1"])
    def test_mqtt_port_out_of_range_is_rejected(
        self, monkeypatch: pytest.MonkeyPatch, port: str
    ) -> None:
        _set_required(monkeypatch)
        monkeypatch.setenv("OWP_MQTT_PORT", port)

        with pytest.raises(ValidationError):
            Settings()

    @pytest.mark.parametrize("qos", ["-1", "3"])
    def test_mqtt_qos_out_of_range_is_rejected(
        self, monkeypatch: pytest.MonkeyPatch, qos: str
    ) -> None:
        _set_required(monkeypatch)
        monkeypatch.setenv("OWP_MQTT_QOS", qos)

        with pytest.raises(ValidationError):
            Settings()

    @pytest.mark.parametrize(
        "name,value",
        [
            ("OWP_DB_POOL_MIN_SIZE", "0"),
            ("OWP_DB_POOL_MAX_SIZE", "0"),
            ("OWP_DB_WRITE_MAX_ATTEMPTS", "0"),
            ("OWP_DB_WRITE_INITIAL_DELAY", "0"),
            ("OWP_DB_WRITE_MAX_DELAY", "0"),
            ("OWP_RECONNECT_INITIAL_DELAY", "0"),
            ("OWP_RECONNECT_MAX_DELAY", "0"),
            ("OWP_DB_COMMAND_TIMEOUT", "0"),
        ],
    )
    def test_positive_numeric_constraints_are_enforced(
        self,
        monkeypatch: pytest.MonkeyPatch,
        name: str,
        value: str,
    ) -> None:
        _set_required(monkeypatch)
        monkeypatch.setenv(name, value)

        with pytest.raises(ValidationError):
            Settings()


class TestDotEnvFile:
    """An ``.env`` file in the CWD is honoured."""

    def test_dotenv_file_is_loaded(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """We re-chdir into ``tmp_path`` to a directory containing a
        ``.env`` file, then assert Settings picks values up from it."""

        env_file = tmp_path / ".env"
        env_file.write_text(
            "OWP_MQTT_HOST=via-dotenv\n"
            "OWP_DATABASE_URL=postgresql://x:x@127.0.0.1:5432/y\n"
            "OWP_MQTT_PORT=8884\n",
            encoding="utf-8",
        )
        monkeypatch.chdir(tmp_path)

        settings = Settings()

        assert settings.mqtt_host == "via-dotenv"
        assert settings.mqtt_port == 8884
