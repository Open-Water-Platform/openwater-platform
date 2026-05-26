"""Asyncio entrypoint for the ingestion service.

Owns the long-running supervisor loop that keeps the MQTT subscriber alive:
on any ``MqttError`` (broker down, network blip, auth rejection) the
subscriber is restarted with exponential backoff so the service stays up
through transient broker outages.

Also owns the lifecycle of the database connection pool: it is opened
once at startup, shared with the subscriber via
:meth:`Database.write_event`, and closed cleanly on shutdown.

The synchronous :func:`run` function is the console-script entry point
declared in ``pyproject.toml``.
"""

from __future__ import annotations

import asyncio
import logging
import signal
import sys

import aiomqtt

from .config import Settings, load_settings
from .db import Database
from .mqtt_client import run_subscriber

logger = logging.getLogger(__name__)


def _configure_logging(level: str) -> None:
    """Initialise root logging once, in a format suited to ``journalctl``."""

    logging.basicConfig(
        level=level.upper(),
        format="%(asctime)s %(levelname)-8s %(name)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S%z",
    )


async def _supervise(
    settings: Settings,
    database: Database,
    stop: asyncio.Event,
) -> None:
    """Run the subscriber forever, reconnecting on broker errors.

    Backoff starts at ``settings.reconnect_initial_delay`` and doubles up
    to ``settings.reconnect_max_delay``. The loop exits cleanly when
    ``stop`` is set (e.g. by a SIGINT/SIGTERM handler). The database is
    shared across reconnect attempts so the pool stays warm even when
    the broker drops.
    """

    delay = settings.reconnect_initial_delay

    while not stop.is_set():
        try:
            await run_subscriber(settings, handler=database.write_event)
        except aiomqtt.MqttError as exc:
            logger.warning(
                "MQTT connection error: %s; retrying in %.1fs",
                exc,
                delay,
            )
        except asyncio.CancelledError:
            raise
        else:
            logger.info("subscriber exited cleanly; retrying in %.1fs", delay)

        if stop.is_set():
            break

        try:
            await asyncio.wait_for(stop.wait(), timeout=delay)
        except asyncio.TimeoutError:
            pass
        else:
            break

        delay = min(delay * 2, settings.reconnect_max_delay)


def _install_signal_handlers(loop: asyncio.AbstractEventLoop, stop: asyncio.Event) -> None:
    """Wire SIGINT/SIGTERM into the stop event for graceful shutdown.

    Falls back silently on platforms (notably Windows) where
    ``loop.add_signal_handler`` is unavailable; KeyboardInterrupt still
    works on those platforms via the default behaviour.
    """

    def _request_stop() -> None:
        if not stop.is_set():
            logger.info("shutdown signal received")
            stop.set()

    for sig_name in ("SIGINT", "SIGTERM"):
        sig = getattr(signal, sig_name, None)
        if sig is None:
            continue
        try:
            loop.add_signal_handler(sig, _request_stop)
        except NotImplementedError:
            continue


async def _async_main() -> None:
    settings = load_settings()
    _configure_logging(settings.log_level)

    logger.info(
        "owp-ingestion starting topic=%s reconnect=%.1fs-%.1fs",
        settings.mqtt_topic,
        settings.reconnect_initial_delay,
        settings.reconnect_max_delay,
    )

    stop = asyncio.Event()
    _install_signal_handlers(asyncio.get_running_loop(), stop)

    database = Database(settings)
    await database.connect()

    try:
        await _supervise(settings, database, stop)
    finally:
        await database.close()
        logger.info("owp-ingestion stopped")


def run() -> None:
    """Console-script entry point."""

    try:
        asyncio.run(_async_main())
    except KeyboardInterrupt:
        sys.exit(130)


if __name__ == "__main__":
    run()
