from __future__ import annotations

from fastapi import APIRouter
from .draft_crud_routes import router as crud_router, get_pending_drafts, dismiss_draft, dismiss_all_drafts
from .draft_publish_routes import router as pub_router, approve_and_publish_draft, approve_all_pending_drafts

router = APIRouter()
router.include_router(crud_router)
router.include_router(pub_router)
