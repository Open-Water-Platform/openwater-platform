"""Unit tests for the v1 MQTT payload models.

These tests pin the *contract* that devices and downstream consumers
depend on. Adding a field, relaxing a constraint, or accepting an
extra unknown attribute should all show up here as a deliberate test
change, not a silent behavioural drift.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from owp_ingestion.models import Location, Reading, ReadingEvent


pytestmark = pytest.mark.unit


_VALID_EVENT_JSON = (
    '{'
    '"device_id": "owp-0001",'
    '"timestamp": "2026-05-24T19:22:30Z",'
    '"firmware_version": "0.1.0",'
    '"location": {"lat": 12.34, "lon": 56.78},'
    '"readings": ['
    '{"parameter": "temperature", "value": 21.5, "unit": "C"},'
    '{"parameter": "ph", "value": 7.2, "unit": "pH"}'
    ']'
    '}'
)


class TestReading:
    """``Reading`` validates one measured value."""

    def test_valid_reading_parses(self) -> None:
        reading = Reading(parameter="temperature", value=21.5, unit="C")

        assert reading.parameter == "temperature"
        assert reading.value == 21.5
        assert reading.unit == "C"

    def test_integer_value_is_coerced_to_float(self) -> None:
        reading = Reading(parameter="ph", value=7, unit="pH")

        assert reading.value == 7.0
        assert isinstance(reading.value, float)

    @pytest.mark.parametrize("field", ["parameter", "value", "unit"])
    def test_missing_required_field_is_rejected(self, field: str) -> None:
        payload = {"parameter": "temperature", "value": 21.5, "unit": "C"}
        payload.pop(field)

        with pytest.raises(ValidationError):
            Reading(**payload)

    @pytest.mark.parametrize(
        "field,value",
        [
            ("parameter", ""),
            ("parameter", "x" * 65),
            ("unit", ""),
            ("unit", "x" * 33),
        ],
    )
    def test_string_length_constraints_are_enforced(
        self, field: str, value: str
    ) -> None:
        payload: dict[str, object] = {
            "parameter": "temperature",
            "value": 21.5,
            "unit": "C",
        }
        payload[field] = value

        with pytest.raises(ValidationError):
            Reading(**payload)

    def test_non_numeric_value_is_rejected(self) -> None:
        with pytest.raises(ValidationError):
            Reading(parameter="temperature", value="hot", unit="C")  # type: ignore[arg-type]

    def test_unknown_field_is_rejected(self) -> None:
        with pytest.raises(ValidationError):
            Reading(
                parameter="temperature",
                value=21.5,
                unit="C",
                quality="good",  # type: ignore[call-arg]
            )


class TestLocation:
    """``Location`` validates lat/lon ranges and rejects extras."""

    def test_valid_location_parses(self) -> None:
        loc = Location(lat=12.34, lon=56.78)

        assert loc.lat == 12.34
        assert loc.lon == 56.78

    @pytest.mark.parametrize("lat,lon", [(-90.0, -180.0), (90.0, 180.0), (0.0, 0.0)])
    def test_boundary_values_are_accepted(self, lat: float, lon: float) -> None:
        loc = Location(lat=lat, lon=lon)

        assert loc.lat == lat
        assert loc.lon == lon

    @pytest.mark.parametrize(
        "lat,lon",
        [
            (-90.1, 0.0),
            (90.1, 0.0),
            (0.0, -180.1),
            (0.0, 180.1),
        ],
    )
    def test_out_of_range_is_rejected(self, lat: float, lon: float) -> None:
        with pytest.raises(ValidationError):
            Location(lat=lat, lon=lon)

    def test_unknown_field_is_rejected(self) -> None:
        with pytest.raises(ValidationError):
            Location(lat=0.0, lon=0.0, alt=100.0)  # type: ignore[call-arg]


class TestReadingEvent:
    """``ReadingEvent`` is the top-level payload contract for v1."""

    def test_full_event_parses(self, sample_reading_event: ReadingEvent) -> None:
        assert sample_reading_event.device_id == "owp-test-0001"
        assert sample_reading_event.firmware_version == "0.1.0"
        assert sample_reading_event.location is not None
        assert len(sample_reading_event.readings) == 2

    def test_minimal_event_parses(
        self, sample_reading_event_minimal: ReadingEvent
    ) -> None:
        assert sample_reading_event_minimal.firmware_version is None
        assert sample_reading_event_minimal.location is None
        assert len(sample_reading_event_minimal.readings) == 1

    def test_readme_example_payload_parses(self) -> None:
        """The example JSON in the README and the model must agree.

        If this test fails after a model change, update the README example
        in lockstep so device authors keep getting accurate guidance.
        """

        event = ReadingEvent.model_validate_json(_VALID_EVENT_JSON)

        assert event.device_id == "owp-0001"
        assert event.location is not None
        assert event.location.lat == 12.34
        assert len(event.readings) == 2

    @pytest.mark.parametrize("field", ["device_id", "timestamp", "readings"])
    def test_required_fields_are_required(self, field: str) -> None:
        payload: dict[str, object] = {
            "device_id": "owp-0001",
            "timestamp": "2026-05-24T19:22:30Z",
            "readings": [{"parameter": "ph", "value": 7.0, "unit": "pH"}],
        }
        payload.pop(field)

        with pytest.raises(ValidationError):
            ReadingEvent.model_validate(payload)

    def test_empty_readings_list_is_rejected(self) -> None:
        """At least one reading is required; an empty payload would be
        an event that measured nothing, which we treat as malformed."""

        with pytest.raises(ValidationError):
            ReadingEvent(
                device_id="owp-0001",
                timestamp=datetime(2026, 5, 24, tzinfo=timezone.utc),
                readings=[],
            )

    @pytest.mark.parametrize(
        "device_id",
        ["", "x" * 129],
    )
    def test_device_id_length_constraints(self, device_id: str) -> None:
        with pytest.raises(ValidationError):
            ReadingEvent(
                device_id=device_id,
                timestamp=datetime(2026, 5, 24, tzinfo=timezone.utc),
                readings=[Reading(parameter="ph", value=7.0, unit="pH")],
            )

    def test_firmware_version_max_length(self) -> None:
        with pytest.raises(ValidationError):
            ReadingEvent(
                device_id="owp-0001",
                timestamp=datetime(2026, 5, 24, tzinfo=timezone.utc),
                firmware_version="x" * 33,
                readings=[Reading(parameter="ph", value=7.0, unit="pH")],
            )

    def test_timestamp_accepts_iso_string(self) -> None:
        event = ReadingEvent.model_validate(
            {
                "device_id": "owp-0001",
                "timestamp": "2026-05-24T19:22:30Z",
                "readings": [{"parameter": "ph", "value": 7.0, "unit": "pH"}],
            }
        )

        assert event.timestamp.year == 2026
        assert event.timestamp.month == 5

    def test_timestamp_accepts_datetime_object(self) -> None:
        ts = datetime(2026, 5, 24, 19, 22, 30, tzinfo=timezone.utc)
        event = ReadingEvent(
            device_id="owp-0001",
            timestamp=ts,
            readings=[Reading(parameter="ph", value=7.0, unit="pH")],
        )

        assert event.timestamp == ts

    def test_unknown_top_level_field_is_rejected(self) -> None:
        """``extra="forbid"`` is the safety net that surfaces new payload
        versions as validation errors rather than silently losing data."""

        with pytest.raises(ValidationError):
            ReadingEvent.model_validate(
                {
                    "device_id": "owp-0001",
                    "timestamp": "2026-05-24T19:22:30Z",
                    "readings": [
                        {"parameter": "ph", "value": 7.0, "unit": "pH"}
                    ],
                    "schema_version": 2,
                }
            )

    def test_unknown_field_inside_reading_is_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ReadingEvent.model_validate(
                {
                    "device_id": "owp-0001",
                    "timestamp": "2026-05-24T19:22:30Z",
                    "readings": [
                        {
                            "parameter": "ph",
                            "value": 7.0,
                            "unit": "pH",
                            "calibrated": True,
                        }
                    ],
                }
            )
