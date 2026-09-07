from __future__ import annotations

from fastapi import APIRouter

from .persona_card_routes import (
    router as card_router,
    get_profile_persona,
    update_profile_persona,
    ImportCardRequest,
    import_profile_character_card,
)
from .diary_memory_routes import (
    router as diary_router,
    get_profile_diary_logs,
    get_profile_memories,
    get_profile_relationships,
    get_profile_strategy,
    update_profile_strategy,
    get_profile_learned_state,
    update_profile_learned_state,
    trigger_profile_reflection,
)
from .kol_channel_routes import (
    router as kol_router,
    get_profile_kol_channels,
    toggle_kol_channel_status,
)

router = APIRouter()
router.include_router(card_router)
router.include_router(diary_router)
router.include_router(kol_router)

__all__ = [
    router,
    get_profile_persona,
    update_profile_persona,
    ImportCardRequest,
    import_profile_character_card,
    get_profile_diary_logs,
    get_profile_memories,
    get_profile_relationships,
    get_profile_strategy,
    update_profile_strategy,
    get_profile_learned_state,
    update_profile_learned_state,
    trigger_profile_reflection,
    get_profile_kol_channels,
    toggle_kol_channel_status,
]
