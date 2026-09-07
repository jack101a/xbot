from __future__ import annotations

from fastapi import APIRouter

from .live_post_routes import (
    router as live_post_router,
    LivePostRequest,
    LiveReplyRequest,
    LivePollRequest,
    LiveThreadRequest,
    publish_live_post,
    publish_live_reply,
    publish_live_poll,
    publish_live_thread,
)
from .live_action_routes import (
    router as live_action_router,
    LiveFollowRequest,
    LiveLikeRequest,
    follow_user_live,
    like_tweet_live,
)

router = APIRouter()
router.include_router(live_post_router)
router.include_router(live_action_router)
