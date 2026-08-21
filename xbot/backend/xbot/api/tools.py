import logging
from typing import Any
from fastapi import APIRouter
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/tools", tags=["Tools"])


class AnalyticsRequest(BaseModel):
    username: str


@router.post("/analytics")
async def get_free_analytics(req: AnalyticsRequest) -> dict[str, Any]:
    """
    Deprecated: Free analytics scraper sandbox has been removed.
    """
    clean_username = req.username.lstrip("@")
    return {
        "status": "deprecated",
        "message": f"Dedicated scraper profile sandbox for @{clean_username} has been removed.",
    }


