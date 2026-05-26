"""MQTT subscriber loop with manual acknowledgement.

Connects to the configured broker, subscribes to the readings topic,
validates each incoming message against :class:`ReadingEvent`, and hands
the result to a dispatch callback. The callback (typically
:meth:`Database.write_event`) may either succeed, fail with
:class:`WriteFailedError` after exhausting its in-process retries, or
raise something unexpected.

The subscriber acknowledges messages manually so the broker can
redeliver any message we did not successfully process:

* Successful write -> ACK; broker drops the message.
* Permanently invalid payload (bad JSON, schema violation, non-bytes
  body) -> ACK; the message would just fail again on redelivery, so we
  drop it on our side and log it.
* :class:`WriteFailedError` from the handler -> **no ACK**; broker
  redelivers on next reconnect. This is the durability backstop that
  protects against service crashes and prolonged DB outages.
* Any other unexpected exception from the handler -> no ACK and a
  full traceback in the logs.
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import Final

import aiomqtt
from pydantic import ValidationError

from .config import Settings
from .db import WriteFailedError
from .models import ReadingEvent

logger = logging.getLogger(__name__)

EventHandler = Callable[[ReadingEvent], Awaitable[None]]

_READINGS_TOPIC_DEVICE_SEGMENT: Final[int] = 3
"""Index of the {device_id} segment in 'owp/v1/devices/{device_id}/readings'."""


async def _log_event(event: ReadingEvent) -> None:
    """Fallback handler used when no DB writer is supplied (e.g. in tests).

    Real production runs always pass :meth:`Database.write_event` from
    :mod:`.main`; this fallback exists so :func:`run_subscriber` stays
    usable in isolation.
    """

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
    supervisor (in ``main.py``) can apply its backoff policy. Per-message
    errors are caught here so a single bad payload cannot kill the loop;
    only connection-level failures propagate.
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
        # Enable manual ack on the underlying paho client. aiomqtt
        # intentionally does not surface this in its public API, but the
        # paho `manual_ack_set` toggle is the supported way to keep
        # PUBACK responsibility on the application side.
        client._client.manual_ack_set(True)

        await client.subscribe(settings.mqtt_topic, qos=settings.mqtt_qos)
        logger.info(
            "subscribed topic=%s qos=%d manual_ack=true",
            settings.mqtt_topic,
            settings.mqtt_qos,
        )

        async for message in client.messages:
            await _handle_message(client, message, on_event)


async def _handle_message(
    client: aiomqtt.Client,
    message: aiomqtt.Message,
    on_event: EventHandler,
) -> None:
    """Validate a single MQTT message, forward it, and ack on success.

    Acks for permanently-rejected payloads happen here too, so the
    broker doesn't redeliver something that will only fail again.
    Withholding an ack (the failure paths below) is what causes broker
    redelivery on next reconnect.
    """

    topic = str(message.topic)
    payload = message.payload

    if not isinstance(payload, (bytes, bytearray)):
        logger.warning("ignoring non-bytes payload topic=%s", topic)
        _ack(client, message)
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
        _ack(client, message)
        return
    except ValueError as exc:
        logger.warning("malformed JSON topic=%s error=%s", topic, exc)
        _ack(client, message)
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
    except WriteFailedError:
        logger.error(
            "write failed terminally device_id=%s timestamp=%s; withholding ack "
            "for broker redelivery",
            event.device_id,
            event.timestamp.isoformat(),
        )
        return
    except Exception:
        logger.exception(
            "event handler raised unexpectedly device_id=%s timestamp=%s; "
            "withholding ack for broker redelivery",
            event.device_id,
            event.timestamp.isoformat(),
        )
        return

    _ack(client, message)


def _ack(client: aiomqtt.Client, message: aiomqtt.Message) -> None:
    """Send a PUBACK for ``message`` via the underlying paho client.

    paho's ``ack`` is synchronous; it merely enqueues the PUBACK on
    paho's send buffer and returns, so calling it from async code is
    safe. Returns no value; failures (unknown mid, already-acked) are
    paho's responsibility to log.
    """

    client._client.ack(message.mid, message.qos)
