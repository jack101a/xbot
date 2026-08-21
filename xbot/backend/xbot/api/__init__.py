from fastapi import APIRouter

from xbot.api.content import router as content_router
from xbot.api.profiles import router as profiles_router
from xbot.api.sessions import router as sessions_router
from xbot.api.system import router as system_router
from xbot.api.tools import router as tools_router

api_router = APIRouter()
api_router.include_router(profiles_router, prefix="/api")
api_router.include_router(sessions_router, prefix="/api")
api_router.include_router(content_router, prefix="/api")
api_router.include_router(system_router, prefix="/api")
api_router.include_router(tools_router, prefix="/api")
