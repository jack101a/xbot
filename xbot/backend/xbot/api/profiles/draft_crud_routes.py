from __future__ import annotations

import asyncio
import datetime
import json
import logging
import os
import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from xbot.config import settings
from xbot.database import get_db
from xbot.models.profile import Profile, ProfileStatus
from xbot.models.content import Content, ContentStatus, ContentType

logger = logging.getLogger("xbot.api.profiles")
router = APIRouter()


@router.get("/{profile_id}/drafts", response_model=list[dict[str, Any]])
async def get_pending_drafts(
    profile_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """Retrieves all pending drafts requiring user review/approval."""
    result = await db.execute(select(Profile).where(Profile.id == profile_id))
    db_profile = result.scalar_one_or_none()
    if not db_profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    stmt = (
        select(Content)
        .where(Content.profile_id == profile_id)
        .where(Content.status.in_([ContentStatus.DRAFT, ContentStatus.APPROVED]))
        .order_by(Content.created_at.desc())
    )
    res = await db.execute(stmt)
    drafts = res.scalars().all()

    result_list = []
    for d in drafts:
        t_items = []
        if getattr(d, "thread_items", None) and len(d.thread_items) > 0:
            t_items = [
                {
                    "id": str(item.id),
                    "position": item.position,
                    "item_type": item.item_type,
                    "text": item.text,
                }
                for item in d.thread_items
            ]
        elif d.ai_metadata and "thread_items" in d.ai_metadata and isinstance(d.ai_metadata["thread_items"], list):
            raw_items = d.ai_metadata["thread_items"]
            t_items = [
                {
                    "id": f"ti-{idx}",
                    "position": idx,
                    "item_type": "hook" if idx == 0 else ("closer" if idx == len(raw_items) - 1 else "body"),
                    "text": item if isinstance(item, str) else item.get("text", ""),
                }
                for idx, item in enumerate(raw_items)
            ]
        elif d.ai_metadata and "tweets" in d.ai_metadata and isinstance(d.ai_metadata["tweets"], list):
            raw_tweets = d.ai_metadata["tweets"]
            t_items = [
                {
                    "id": f"ti-{idx}",
                    "position": idx,
                    "item_type": "hook" if idx == 0 else ("closer" if idx == len(raw_tweets) - 1 else "body"),
                    "text": item,
                }
                for idx, item in enumerate(raw_tweets)
            ]

        result_list.append({
            "id": str(d.id),
            "content_type": d.content_type.value if hasattr(d.content_type, "value") else str(d.content_type),
            "body": d.body,
            "status": d.status.value if hasattr(d.status, "value") else str(d.status),
            "ai_metadata": d.ai_metadata,
            "thread_items": t_items,
            "created_at": d.created_at.isoformat() if d.created_at else None,
        })
    return result_list


@router.delete("/{profile_id}/drafts/{content_id}", response_model=dict[str, Any])
async def dismiss_draft(
    profile_id: uuid.UUID,
    content_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Dismisses/deletes a single pending draft."""
    c_res = await db.execute(select(Content).where(Content.id == content_id).where(Content.profile_id == profile_id))
    draft = c_res.scalar_one_or_none()
    if not draft:
        raise HTTPException(status_code=404, detail="Draft content not found")

    await db.delete(draft)
    await db.commit()
    return {"status": "success", "message": "Draft dismissed."}


@router.delete("/{profile_id}/drafts", response_model=dict[str, Any])
async def dismiss_all_drafts(
    profile_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Dismisses/deletes ALL pending drafts for a profile in bulk."""
    stmt = (
        delete(Content)
        .where(Content.profile_id == profile_id)
        .where(Content.status.in_([ContentStatus.DRAFT, ContentStatus.APPROVED]))
    )
    res = await db.execute(stmt)
    await db.commit()
    return {
        "status": "success",
        "message": f"All {res.rowcount} pending drafts discarded.",
        "discarded_count": res.rowcount,
    }
