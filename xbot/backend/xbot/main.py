from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from xbot.api import api_router
from xbot.config import settings

app = FastAPI(
    title="XBot API Server",
    description="Backend API services for XBot Twitter Automation System",
    version="0.1.0",
)

# Set up CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router)


@app.get("/health")
async def health_check() -> dict[str, Any]:
    """
    Health check endpoint returning system status.
    """
    return {
        "status": "healthy",
        "service": "xbot-api",
        "version": "0.1.0",
        "database_configured": bool(settings.DATABASE_URL),
        "redis_configured": bool(settings.REDIS_URL),
    }


# Mount lightweight static dashboard SPA directly
static_dashboard_dir = Path(__file__).resolve().parent.parent.parent / "dashboard" / "out"
if static_dashboard_dir.exists():
    app.mount("/", StaticFiles(directory=str(static_dashboard_dir), html=True), name="static_dashboard")
else:
    @app.get("/")
    async def root() -> dict[str, str]:
        return {"message": "Welcome to XBot API Server"}
