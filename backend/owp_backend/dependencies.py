"""FastAPI dependency providers."""

from __future__ import annotations

from functools import lru_cache
from typing import Annotated

from fastapi import Depends, Request

from .config import Settings, load_settings
from .db import Database


@lru_cache
def get_settings() -> Settings:
    """Return cached settings for the process lifetime."""

    return load_settings()


def get_database(request: Request) -> Database:
    """Return the shared database instance from application state."""

    return request.app.state.database


SettingsDep = Annotated[Settings, Depends(get_settings)]
DatabaseDep = Annotated[Database, Depends(get_database)]
