from __future__ import annotations
from fastapi import APIRouter
from .health_routes import router as health_router
from .config_routes import router as config_router

router = APIRouter()
router.include_router(health_router)
router.include_router(config_router)

__all__ = ["router"]
