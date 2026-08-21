from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from pydantic import BaseModel
from xbot.database import get_db
from xbot.models.content import Content

router = APIRouter(tags=["Content"])


@router.get("/profiles/{profile_id}/content", response_model=list[dict[str, Any]])
async def list_profile_content(
    profile_id: uuid.UUID,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """Lists recent posts (draft, posted, failed) generated for a profile."""
    stmt = (
        select(Content)
        .where(Content.profile_id == profile_id)
        .order_by(Content.created_at.desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    content_list = result.scalars().all()

    return [
        {
            "id": c.id,
            "profile_id": c.profile_id,
            "content_type": c.content_type,
            "body": c.body,
            "status": c.status,
            "tweet_id": c.tweet_id,
            "performance": c.performance,
            "posted_at": c.posted_at,
            "created_at": c.created_at,
        }
        for c in content_list
    ]


@router.get("/content/{content_id}", response_model=dict[str, Any])
async def get_content_detail(
    content_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Gets details of a single post item with performance/AI metadata."""
    stmt = select(Content).where(Content.id == content_id)
    result = await db.execute(stmt)
    c = result.scalar_one_or_none()
    if not c:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Content not found."
        )

    return {
        "id": c.id,
        "profile_id": c.profile_id,
        "content_type": c.content_type,
        "body": c.body,
        "status": c.status,
        "tweet_id": c.tweet_id,
        "performance": c.performance,
        "ai_metadata": c.ai_metadata,
        "posted_at": c.posted_at,
        "created_at": c.created_at,
    }


class UpdateContentStatusRequest(BaseModel):
    status: str

@router.put("/content/{content_id}/status", response_model=dict[str, Any])
async def update_content_status(
    content_id: uuid.UUID,
    req: UpdateContentStatusRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Updates the status of a content item (e.g. approve/post or reject/fail)."""
    stmt = select(Content).where(Content.id == content_id)
    result = await db.execute(stmt)
    c = result.scalar_one_or_none()
    if not c:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Content not found."
        )

    # Allow setting posted or failed
    if req.status.lower() == "posted":
        from datetime import datetime
        c.status = "posted"
        c.posted_at = datetime.utcnow()
    elif req.status.lower() == "failed":
        c.status = "failed"
    else:
        c.status = req.status

    await db.commit()
    return {"status": "success", "message": f"Content status updated to {c.status}"}


class GenerateContentRequest(BaseModel):
    context_prompt: str
    max_chars: int = 280

@router.post("/profiles/{profile_id}/generate", response_model=dict[str, Any])
async def generate_ai_content(
    profile_id: uuid.UUID,
    req: GenerateContentRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Generates AI content for a profile based on a prompt."""
    from xbot.models.profile import Profile
    from xbot.ai.generator import ContentGenerator

    stmt = select(Profile).where(Profile.id == profile_id)
    res = await db.execute(stmt)
    profile = res.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found.")

    generator = ContentGenerator()
    try:
        generated = await generator.generate_content(
            db=db,
            profile_slug=profile.profile_slug,
            context_prompt=req.context_prompt,
            max_chars=req.max_chars,
        )
        return {
            "status": "success",
            "primary_text": generated.primary_text,
            "alternatives": generated.alternatives,
            "suggested_hashtags": generated.suggested_hashtags
        }
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
