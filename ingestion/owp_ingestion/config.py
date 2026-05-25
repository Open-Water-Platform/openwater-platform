"""Runtime configuration for the ingestion service.

All settings are read from environment variables (prefix ``OWP_``) and
optionally a local ``.env`` file. No defaults are provided for connection
details that the operator must consciously choose (``mqtt_host``), so the
service fails fast with a clear error if it is misconfigured.
"""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment-driven settings for the ingestion service."""

    model_config = SettingsConfigDict(
        env_prefix="OWP_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    mqtt_host: str = Field(
        ...,
        description="Hostname or IP of the MQTT broker the service subscribes to.",
    )
    mqtt_port: int = Field(
        default=1883,
        ge=1,
        le=65535,
        description="TCP port of the MQTT broker.",
    )
    mqtt_username: str | None = Field(
        default=None,
        description="Optional MQTT username for broker authentication.",
    )
    mqtt_password: str | None = Field(
        default=None,
        description="Optional MQTT password for broker authentication.",
    )
    mqtt_topic: str = Field(
        default="owp/v1/devices/+/readings",
        description=(
            "MQTT topic filter to subscribe to. Defaults to the v1 readings "
            "wildcard across all devices."
        ),
    )
    mqtt_client_id: str = Field(
        default="owp-ingestion",
        description="MQTT client identifier reported to the broker.",
    )
    mqtt_qos: int = Field(
        default=1,
        ge=0,
        le=2,
        description="MQTT quality-of-service level used for the subscription.",
    )

    reconnect_initial_delay: float = Field(
        default=1.0,
        gt=0,
        description="Initial backoff (seconds) after a broker disconnect.",
    )
    reconnect_max_delay: float = Field(
        default=30.0,
        gt=0,
        description="Maximum backoff (seconds) between reconnect attempts.",
    )

    log_level: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).",
    )


def load_settings() -> Settings:
    """Load settings from the environment.

    Wrapping construction in a function keeps import-time side effects out
    of modules that only need the type, and makes settings easy to override
    in future tests.
    """

    return Settings()
