"""MQTT subscriber loop.

Connects to the configured broker, subscribes to the readings topic,
validates each incoming message against :class:`ReadingEvent`, and hands
the result to a dispatch callback. For the current slice the default
callback just logs; once a database layer lands, the writer plugs in
here without touching this module.
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import Final

import aiomqtt
from pydantic import ValidationError

from .config import Settings
from .models import ReadingEvent

logger = logging.getLogger(__name__)

EventHandler = Callable[[ReadingEvent], Awaitable[None]]

_READINGS_TOPIC_DEVICE_SEGMENT: Final[int] = 3
"""Index of the {device_id} segment in 'owp/v1/devices/{device_id}/readings'."""


async def _log_event(event: ReadingEvent) -> None:
    """Default handler: structured log line for each validated event."""

    logger.info(
        "received reading event device_id=%s timestamp=%s readings=%d firmware=%s",
        event.device_id,
        event.timestamp.isoformat(),
        len(event.readings),
        event.firmware_version or "unknown",
    )


def _device_id_from_topic(topic: str) -> str | None:
    """Return the device id segment of a readings topic, or None if absent.

    Topics that do not match the expected ``owp/v1/devices/{id}/readings``
    shape simply return ``None``; the caller decides how to react.
    """

    segments = topic.split("/")
    if len(segments) <= _READINGS_TOPIC_DEVICE_SEGMENT:
        return None
    return segments[_READINGS_TOPIC_DEVICE_SEGMENT]


async def run_subscriber(
    settings: Settings,
    handler: EventHandler | None = None,
) -> None:
    """Connect to the broker and process readings until cancelled.

    Raises :class:`aiomqtt.MqttError` on connection failure so the outer
    supervisor (in ``main.py``) can apply its backoff policy. All
    per-message errors (invalid JSON, schema violations) are caught and
    logged so a single bad payload cannot stop the subscriber.
    """

    on_event = handler or _log_event

    logger.info(
        "connecting to MQTT broker host=%s port=%d client_id=%s",
        settings.mqtt_host,
        settings.mqtt_port,
        settings.mqtt_client_id,
    )

    async with aiomqtt.Client(
        hostname=settings.mqtt_host,
        port=settings.mqtt_port,
        username=settings.mqtt_username,
        password=settings.mqtt_password,
        identifier=settings.mqtt_client_id,
    ) as client:
        await client.subscribe(settings.mqtt_topic, qos=settings.mqtt_qos)
        logger.info(
            "subscribed topic=%s qos=%d",
            settings.mqtt_topic,
            settings.mqtt_qos,
        )

        async for message in client.messages:
            await _handle_message(message, on_event)


async def _handle_message(
    message: aiomqtt.Message,
    on_event: EventHandler,
) -> None:
    """Validate a single MQTT message and forward it to ``on_event``.

    Validation and dispatch errors are caught and logged here; they never
    propagate so that one bad payload cannot kill the subscriber loop.
    """

    topic = str(message.topic)
    payload = message.payload

    if not isinstance(payload, (bytes, bytearray)):
        logger.warning("ignoring non-bytes payload topic=%s", topic)
        return

    try:
        event = ReadingEvent.model_validate_json(payload)
    except ValidationError as exc:
        logger.warning(
            "rejected payload topic=%s errors=%d preview=%r",
            topic,
            exc.error_count(),
            payload[:200],
        )
        return
    except ValueError as exc:
        logger.warning("malformed JSON topic=%s error=%s", topic, exc)
        return

    topic_device_id = _device_id_from_topic(topic)
    if topic_device_id is not None and topic_device_id != event.device_id:
        logger.warning(
            "device_id mismatch topic=%s topic_device_id=%s payload_device_id=%s",
            topic,
            topic_device_id,
            event.device_id,
        )

    try:
        await on_event(event)
    except Exception:  # pragma: no cover - defensive
        logger.exception(
            "event handler failed device_id=%s timestamp=%s",
            event.device_id,
            event.timestamp.isoformat(),
        )
