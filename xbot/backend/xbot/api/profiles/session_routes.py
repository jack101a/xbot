from __future__ import annotations

from fastapi import APIRouter

from .cookie_auth_routes import (
    router as cookie_router,
    launch_login_session,
    get_profile_auth_status,
    ImportCookiesRequest,
    import_profile_cookies,
    sync_profile_from_x_endpoint,
)
from .crud import trigger_profile_session

router = APIRouter()
router.include_router(cookie_router)

__all__ = [
    router,
    launch_login_session,
    get_profile_auth_status,
    ImportCookiesRequest,
    import_profile_cookies,
    sync_profile_from_x_endpoint,
    trigger_profile_session,
]
