from __future__ import annotations

from fastapi import APIRouter

from .draft_routes import (
    router as draft_router,
    get_pending_drafts,
    approve_and_publish_draft,
    dismiss_draft,
    dismiss_all_drafts,
    approve_all_pending_drafts,
)
from .live_publish_routes import (
    router as live_router,
    LivePostRequest,
    LiveReplyRequest,
    LivePollRequest,
    LiveThreadRequest,
    LiveFollowRequest,
    LiveLikeRequest,
    publish_live_post,
    publish_live_reply,
    publish_live_poll,
    publish_live_thread,
    follow_user_live,
    like_tweet_live,
)
from .media_routes import (
    router as media_router,
    upload_profile_media,
    list_profile_media,
)
from .growth_f4f_routes import (
    router as f4f_router,
    F4FFollowRequest,
    get_f4f_candidates,
    trigger_f4f_scan,
    execute_f4f_follow,
    trigger_growth_and_autofollowback_endpoint,
    get_f4f_stats,
    get_active_growth_posts,
    execute_f4f_batch_follow,
)

router = APIRouter()
router.include_router(draft_router)
router.include_router(live_router)
router.include_router(media_router)
router.include_router(f4f_router)
