"""Runtime configuration for the backend service.

All settings are read from environment variables (prefix ``OWP_``) and
optionally a local ``.env`` file. Connection details the operator must
consciously choose have no defaults so the service fails fast when
misconfigured.
"""

from __future__ import annotations

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment-driven settings for the backend service."""

    model_config = SettingsConfigDict(
        env_prefix="OWP_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = Field(
        ...,
        description=(
            "PostgreSQL connection URL for the asyncpg pool, e.g. "
            "'postgresql://owp:owp@127.0.0.1:5432/owp'."
        ),
    )
    host: str = Field(
        default="0.0.0.0",
        description="HTTP bind address for uvicorn.",
    )
    port: int = Field(
        default=8000,
        ge=1,
        le=65535,
        description="HTTP port for uvicorn.",
    )
    db_pool_min_size: int = Field(
        default=1,
        ge=1,
        description="Minimum number of connections kept open in the asyncpg pool.",
    )
    db_pool_max_size: int = Field(
        default=10,
        ge=1,
        description="Maximum number of connections the asyncpg pool may open.",
    )
    db_command_timeout: float = Field(
        default=10.0,
        gt=0,
        description="Per-statement timeout (seconds) applied by asyncpg.",
    )
    log_level: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).",
    )
    cors_origins: str = Field(
        default="http://localhost:5173",
        description="Comma-separated list of allowed CORS origins.",
    )
    readings_default_limit: int = Field(
        default=100,
        ge=1,
        description="Default page size for readings list endpoints.",
    )
    readings_max_limit: int = Field(
        default=1000,
        ge=1,
        description="Hard cap on readings list page size.",
    )
    devices_default_limit: int = Field(
        default=50,
        ge=1,
        description="Default page size for device list endpoints.",
    )
    devices_max_limit: int = Field(
        default=200,
        ge=1,
        description="Hard cap on device list page size.",
    )

    @field_validator("cors_origins")
    @classmethod
    def _strip_cors_origin_entries(cls, value: str) -> str:
        return ",".join(part.strip() for part in value.split(",") if part.strip())

    @property
    def cors_origin_list(self) -> list[str]:
        """Parse ``cors_origins`` into a list for Starlette middleware."""

        if not self.cors_origins:
            return []
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


def load_settings() -> Settings:
    """Load settings from the environment."""

    return Settings()
