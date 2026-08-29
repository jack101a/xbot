import logging
from fastapi import APIRouter
from xbot.schemas.profile import ProfileResponse
from xbot.browser.manager import BrowserManager
from xbot.browser.actions.sync_profile_action import SyncProfileFromX, SyncProfileAction
from xbot.browser.auth import inspect_profile_auth_status, parse_cookie_string, format_storage_state

router = APIRouter(prefix="/profiles", tags=["Profiles"])

from .crud import router as crud_router, list_profiles, create_profile, get_profile, update_profile, delete_profile, pause_profile, resume_profile, trigger_profile_session, _populate_profile_metrics
from .campaign_routes import router as campaign_routes_router
from .persona_memory_routes import router as persona_memory_routes_router
from .analytics_routes import router as analytics_routes_router
from .session_routes import router as session_routes_router
from .automation_state_routes import router as automation_state_routes_router
from .pruner_routes import router as pruner_routes_router
from .constants import *

# Register empty path aliases for root collection operations
router.add_api_route("", list_profiles, methods=["GET"], response_model=list[ProfileResponse], include_in_schema=False)
router.add_api_route("", create_profile, methods=["POST"], response_model=ProfileResponse, status_code=201, include_in_schema=False)

router.include_router(crud_router)
router.include_router(campaign_routes_router)
router.include_router(persona_memory_routes_router)
router.include_router(analytics_routes_router)
router.include_router(session_routes_router)
router.include_router(automation_state_routes_router)
router.include_router(pruner_routes_router)

# Re-export all endpoint handlers and classes for external modules and tests
from .campaign_routes import (
    get_pending_drafts, approve_and_publish_draft, dismiss_draft, dismiss_all_drafts,
    approve_all_pending_drafts, LivePostRequest, LiveReplyRequest, LivePollRequest,
    LiveThreadRequest, LiveFollowRequest, LiveLikeRequest, publish_live_post,
    publish_live_reply, publish_live_poll, publish_live_thread, follow_user_live,
    like_tweet_live, upload_profile_media, list_profile_media, F4FFollowRequest,
    get_f4f_candidates, trigger_f4f_scan, execute_f4f_follow,
    trigger_growth_and_autofollowback_endpoint, get_f4f_stats, get_active_growth_posts,
    execute_f4f_batch_follow
)
from .persona_memory_routes import (
    get_profile_persona, update_profile_persona, ImportCardRequest,
    import_profile_character_card, get_profile_diary_logs, get_profile_memories,
    get_profile_relationships, get_profile_strategy, update_profile_strategy,
    get_profile_learned_state, update_profile_learned_state, trigger_profile_reflection,
    get_profile_kol_channels, toggle_kol_channel_status
)
from .analytics_routes import (
    get_profile_analytics_snapshots,
    get_profile_monetization_status, get_deep_analytics, sync_live_analytics
)
from .session_routes import (
    launch_login_session, get_profile_auth_status, ImportCookiesRequest,
    import_profile_cookies, sync_profile_from_x_endpoint
)
from .automation_state_routes import (
    get_profile_config, update_profile_config
)
