from __future__ import annotations
import xbot.api.profiles as profiles_api

import logging
import os
import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import yaml

from xbot.config import settings
from xbot.database import get_db
from xbot.models.profile import Profile, ProfileStatus
from xbot.persona.loader import load_persona, save_persona, load_character_card, save_character_card, load_strategy, save_strategy, load_relationships, save_relationships, load_learned_state, save_learned_state, load_config, save_config
from xbot.persona.diary import DiaryManager
from xbot.persona.memory import MemoryManager
from .constants import BASE_PROFILE_DIR

logger = logging.getLogger('xbot.api.profiles')
router = APIRouter()


@router.get("/{profile_id}/persona", response_model=dict[str, Any])
async def get_profile_persona(profile_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    """Retrieves raw persona configuration yaml details."""
    result = await db.execute(select(Profile).where(Profile.id == profile_id))
    db_profile = result.scalar_one_or_none()
    if db_profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found"
        )

    profile_dir = Path(profiles_api.BASE_PROFILE_DIR) / db_profile.profile_slug
    persona = load_persona(profile_dir)
    return persona.model_dump()


@router.put("/{profile_id}/persona", response_model=dict[str, Any])
async def update_profile_persona(
    profile_id: uuid.UUID,
    persona_in: dict[str, Any],
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Updates persona.yaml configurations on disk."""
    result = await db.execute(select(Profile).where(Profile.id == profile_id))
    db_profile = result.scalar_one_or_none()
    if db_profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found"
        )

    profile_dir = Path(profiles_api.BASE_PROFILE_DIR) / db_profile.profile_slug
    persona_file = profile_dir / "persona.yaml"
    with persona_file.open("w", encoding="utf-8") as f:
        yaml.dump(persona_in, f)

    return {"status": "success", "message": "Persona configuration updated successfully."}


class ImportCardRequest(BaseModel):
    content_or_path: str
    use_ai: bool = False


@router.post("/{profile_id}/import-card", response_model=dict[str, Any])
async def import_profile_character_card(
    profile_id: uuid.UUID,
    req: ImportCardRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Loads and parses a character card (JSON/YAML/file path) into our 7-Dimension Bedrock Persona,
    preserving the full raw card anchor to prevent hallucinations.
    """
    result = await db.execute(select(Profile).where(Profile.id == profile_id))
    db_profile = result.scalar_one_or_none()
    if db_profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found"
        )

    try:
        raw_card = load_raw_card(req.content_or_path)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to load character card: {str(e)}"
        )

    persona_dict = map_card_to_persona(raw_card, existing_id=db_profile.profile_slug, existing_slug=db_profile.profile_slug)

    if req.use_ai:
        try:
            from xbot.ai.client import get_ai_client
            from xbot.config import settings
            import json as json_lib
            client = get_ai_client()
            prompt = (
                f"Enhance and refine this persona dictionary into a rich, high-fidelity 7-dimension persona:\n"
                f"{json_lib.dumps(persona_dict, indent=2)}\n\n"
                f"Original raw source:\n{req.content_or_path[:2000]}\n\n"
                f"Return ONLY valid JSON matching the persona schema with rich traits, values, writing rules, and background."
            )
            res = await client.chat.completions.create(
                model=settings.MODEL_POST_CREATION,
                messages=[
                    {"role": "system", "content": "You are an expert persona architect. Return ONLY JSON."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.3
            )
            content_str = res.choices[0].message.content
            if content_str:
                ai_parsed = json_lib.loads(content_str)
                if isinstance(ai_parsed, dict) and "identity" in ai_parsed and "personality" in ai_parsed:
                    ai_parsed["id"] = db_profile.profile_slug
                    ai_parsed["raw_character_card"] = raw_card
                    persona_dict = ai_parsed
        except Exception as e:
            logger.warning(f"AI persona enhancement failed, using deterministic mapping: {e}")

    profile_dir = Path(profiles_api.BASE_PROFILE_DIR) / db_profile.profile_slug
    persona_file = profile_dir / "persona.yaml"
    with persona_file.open("w", encoding="utf-8") as f:
        yaml.dump(persona_dict, f)

    return {
        "status": "success",
        "message": "Character card loaded and mapped successfully.",
        "persona": persona_dict
    }
