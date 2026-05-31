"""HTTP route modules."""

from __future__ import annotations

from fastapi import APIRouter

from .devices import router as devices_router
from .health import router as health_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(devices_router)
