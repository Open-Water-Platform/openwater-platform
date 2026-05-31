"""FastAPI application entrypoint."""

from __future__ import annotations

import logging
import sys
from contextlib import asynccontextmanager
from typing import AsyncIterator

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import Settings, load_settings
from .db import Database
from .routes import api_router

logger = logging.getLogger(__name__)


def _configure_logging(level: str) -> None:
    logging.basicConfig(
        level=level.upper(),
        format="%(asctime)s %(levelname)-8s %(name)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S%z",
    )


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build the FastAPI application."""

    resolved_settings = settings or load_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        database = Database(resolved_settings)
        app.state.database = database
        await database.connect()
        try:
            yield
        finally:
            await database.close()

    app = FastAPI(
        title="Open Water Platform API",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=resolved_settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["GET"],
        allow_headers=["*"],
    )
    app.include_router(api_router)
    return app


app = create_app()


def run() -> None:
    """Console-script entry point."""

    settings = load_settings()
    _configure_logging(settings.log_level)
    logger.info("owp-backend starting host=%s port=%d", settings.host, settings.port)
    try:
        uvicorn.run(
            "owp_backend.main:app",
            host=settings.host,
            port=settings.port,
            log_level=settings.log_level.lower(),
        )
    except KeyboardInterrupt:
        sys.exit(130)


if __name__ == "__main__":
    run()
