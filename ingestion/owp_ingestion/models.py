"""Pydantic models for the MQTT reading payload (v1).

These models are the runtime source of truth for the payload contract the
ingestion service accepts. Once a dedicated ``schemas/`` directory exists,
JSON Schemas will be generated from these models rather than duplicated.

See ``ingestion/README.md`` for the human-readable contract and example
payloads.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class Reading(BaseModel):
    """A single measured value from a sensor on a device."""

    model_config = ConfigDict(extra="forbid")

    parameter: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description=(
            "Name of the measured parameter, e.g. 'temperature', 'ph', "
            "'flow_rate', 'volume'."
        ),
    )
    value: float = Field(
        ...,
        description="Numerical value of the reading in the given unit.",
    )
    unit: str = Field(
        ...,
        min_length=1,
        max_length=32,
        description="Unit of measurement, e.g. 'C', 'pH', 'L/min', 'L'.",
    )


class Location(BaseModel):
    """Geographic location of a device at the time of the reading."""

    model_config = ConfigDict(extra="forbid")

    lat: float = Field(..., ge=-90.0, le=90.0, description="Latitude in degrees.")
    lon: float = Field(..., ge=-180.0, le=180.0, description="Longitude in degrees.")


class ReadingEvent(BaseModel):
    """A single ingest event published by a device to MQTT.

    One event carries every parameter measured at one point in time. Devices
    that only support a subset of parameters include only those they
    actually measure.
    """

    model_config = ConfigDict(extra="forbid")

    device_id: str = Field(
        ...,
        min_length=1,
        max_length=128,
        description=(
            "Unique identifier of the device that produced the reading. Must "
            "match the {device_id} segment of the MQTT topic."
        ),
    )
    timestamp: datetime = Field(
        ...,
        description=(
            "ISO-8601 timestamp of the reading. Devices should emit UTC; "
            "naive timestamps are accepted but downstream consumers may "
            "assume UTC."
        ),
    )
    firmware_version: str | None = Field(
        default=None,
        max_length=32,
        description="Firmware version of the device, e.g. '0.1.0'.",
    )
    location: Location | None = Field(
        default=None,
        description=(
            "Geographic location at the time of the reading. Optional once a "
            "device is registered; useful for the first message from a new "
            "device."
        ),
    )
    readings: list[Reading] = Field(
        ...,
        min_length=1,
        description="One entry per measured parameter; at least one required.",
    )
