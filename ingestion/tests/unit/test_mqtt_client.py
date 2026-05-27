"""Unit tests for the MQTT subscriber's ack/no-ack contract.

The subscriber's job is to translate broker messages into validated
events, hand them to the writer, and decide whether to acknowledge
each message. That decision is the durability hinge of the whole
ingestion service:

* Acked -> broker drops the message.
* Not acked -> broker redelivers on next reconnect.

These tests pin the documented matrix from mqtt_client.py's module
docstring:

* successful write -> ACK
* permanently invalid payload (non-bytes, bad JSON, schema violation)
  -> ACK (would only fail again on redelivery)
* WriteFailedError from the handler -> no ACK
* any other unexpected handler error -> no ACK

Tests call ``_handle_message`` directly with mock client/message
objects; that function is the seam the public ``run_subscriber`` uses
internally, and is where all the logic lives.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from owp_ingestion.db import WriteFailedError
from owp_ingestion.mqtt_client import (
    _device_id_from_topic,
    _handle_message,
)


pytestmark = pytest.mark.unit


_VALID_PAYLOAD = (
    b'{'
    b'"device_id": "owp-0001",'
    b'"timestamp": "2026-05-24T19:22:30Z",'
    b'"readings": ['
    b'{"parameter": "temperature", "value": 21.5, "unit": "C"}'
    b']'
    b'}'
)


def _make_client_and_message(
    topic: str = "owp/v1/devices/owp-0001/readings",
    payload: bytes | bytearray | str = _VALID_PAYLOAD,
    mid: int = 1,
    qos: int = 1,
) -> tuple[MagicMock, MagicMock]:
    """Build a (client, message) pair shaped like aiomqtt's API.

    ``client._client.ack`` is the paho method called for manual
    acknowledgement and is a synchronous ``MagicMock``. The message's
    ``topic`` is a plain string because the production code uses
    ``str(message.topic)`` and a string round-trips to itself.
    """

    client = MagicMock()
    client._client = MagicMock()
    client._client.ack = MagicMock()

    message = MagicMock()
    message.topic = topic
    message.payload = payload
    message.mid = mid
    message.qos = qos
    return client, message


class TestDeviceIdFromTopic:
    """Topic parser used to detect topic/payload device-id mismatches."""

    def test_extracts_device_id_from_v1_readings_topic(self) -> None:
        assert (
            _device_id_from_topic("owp/v1/devices/owp-0001/readings")
            == "owp-0001"
        )

    def test_returns_none_for_too_short_topic(self) -> None:
        assert _device_id_from_topic("owp/v1/devices") is None

    def test_returns_none_for_empty_topic(self) -> None:
        assert _device_id_from_topic("") is None

    def test_handles_extra_segments(self) -> None:
        """Unexpected suffixes are tolerated: we still return the
        device_id segment so downstream comparison can run."""

        assert (
            _device_id_from_topic("owp/v1/devices/owp-0001/readings/extra")
            == "owp-0001"
        )


class TestHandleMessageHappyPath:
    """Valid payload + successful handler => message is acked."""

    async def test_handler_called_with_validated_event(self) -> None:
        client, message = _make_client_and_message()
        handler = AsyncMock()

        await _handle_message(client, message, handler)

        handler.assert_awaited_once()
        event = handler.await_args.args[0]
        assert event.device_id == "owp-0001"
        assert len(event.readings) == 1

    async def test_acks_message_on_success(self) -> None:
        client, message = _make_client_and_message(mid=42, qos=1)
        handler = AsyncMock()

        await _handle_message(client, message, handler)

        client._client.ack.assert_called_once_with(42, 1)


class TestHandleMessageInvalidPayload:
    """Permanently invalid payloads are acked so the broker drops them.

    Withholding the ack here would cause an infinite redelivery loop
    for a message that will never validate, which is worse than the
    data loss it would prevent.
    """

    async def test_non_bytes_payload_is_acked_without_calling_handler(
        self,
    ) -> None:
        client, message = _make_client_and_message(payload="not bytes")
        handler = AsyncMock()

        await _handle_message(client, message, handler)

        handler.assert_not_awaited()
        client._client.ack.assert_called_once()

    async def test_malformed_json_is_acked_without_calling_handler(
        self,
    ) -> None:
        client, message = _make_client_and_message(payload=b"{not valid json")
        handler = AsyncMock()

        await _handle_message(client, message, handler)

        handler.assert_not_awaited()
        client._client.ack.assert_called_once()

    async def test_schema_violation_is_acked_without_calling_handler(
        self,
    ) -> None:
        """A well-formed JSON object that fails ReadingEvent validation
        (missing required ``timestamp`` here) is still permanently bad."""

        client, message = _make_client_and_message(
            payload=b'{"device_id": "owp-0001"}'
        )
        handler = AsyncMock()

        await _handle_message(client, message, handler)

        handler.assert_not_awaited()
        client._client.ack.assert_called_once()


class TestHandleMessageDeviceIdMismatch:
    """Topic device_id != payload device_id is a warning, not a reject.

    The README documents that the service logs the mismatch but still
    accepts the event so minor topic/payload drift cannot block a
    deployment.
    """

    async def test_mismatch_still_calls_handler_and_acks(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        client, message = _make_client_and_message(
            topic="owp/v1/devices/owp-different/readings"
        )
        handler = AsyncMock()

        with caplog.at_level("WARNING", logger="owp_ingestion.mqtt_client"):
            await _handle_message(client, message, handler)

        handler.assert_awaited_once()
        client._client.ack.assert_called_once()
        assert any(
            "mismatch" in record.message for record in caplog.records
        )


class TestHandleMessageHandlerFailures:
    """Handler-side errors decide whether the broker redelivers."""

    async def test_write_failed_error_withholds_ack(self) -> None:
        """The durability backstop: when the write retry budget is
        exhausted, we refuse to ack so the broker redelivers later."""

        client, message = _make_client_and_message()
        handler = AsyncMock(
            side_effect=WriteFailedError("all retries exhausted")
        )

        await _handle_message(client, message, handler)

        handler.assert_awaited_once()
        client._client.ack.assert_not_called()

    async def test_unexpected_handler_exception_withholds_ack(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """An unknown exception type means we don't know whether
        redelivery is safe. We choose redelivery and a loud traceback
        over silent data loss."""

        client, message = _make_client_and_message()
        handler = AsyncMock(side_effect=RuntimeError("unexpected"))

        with caplog.at_level("ERROR", logger="owp_ingestion.mqtt_client"):
            await _handle_message(client, message, handler)

        handler.assert_awaited_once()
        client._client.ack.assert_not_called()
        assert any(
            "withholding ack" in record.message for record in caplog.records
        )
