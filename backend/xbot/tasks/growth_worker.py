from __future__ import annotations
from .common import extract_tweet_id_from_url, _parse_x_counts, has_already_acted, broadcast_session_log, _extract_or_generate_poll_data
from .common import extract_tweet_id_from_url, _parse_x_counts, has_already_acted, broadcast_session_log, _extract_or_generate_poll_data
import asyncio
import datetime
import logging
import random
import uuid
from typing import Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import json
from pathlib import Path
import redis
from xbot.ai.client import get_ai_client
from xbot.ai.growth_scorer import score_tweet_opportunity
from xbot.ai.hook_optimizer import extract_links
from xbot.ai.planner import plan_session
from xbot.ai.poll_generator import generate_poll
from xbot.ai.post_session import PostSessionProcessor
from xbot.ai.sniper import generate_sniper_reply
from xbot.ai.trend_generator import generate_trend_take
from xbot.ai.trend_radar import fetch_rss_trends
from xbot.ai.visual_engine import generate_visual_post_spec
from xbot.browser.actions.poll_action import CreatePoll
from xbot.browser.actions.x_actions import (
    BrowseFeed,
    CheckUserLatestTweet,
    ComposePost,
    FollowEngagers,
    FollowUser,
    LikeTweet,
    QuoteTweet,
    ReplyToTweet,
    Retweet,
    ScrapeFollowList,
    ScrapeProfileMetrics,
    ScrapeTrends,
    SearchQuery,
    UnfollowNonFollowers,
    UnfollowUser,
)
from xbot.browser.actions.selectors import SELECTORS
from xbot.browser.manager import BrowserManager
from xbot.browser.timing import sleep_with_jitter, sleep_think_time
from xbot.celery_app import celery_app
from xbot.config import settings
from xbot.database import AsyncSessionLocal
from xbot.models.analytics import AnalyticsSnapshot
from xbot.models.profile import Profile, ProfileStatus
from xbot.models.content import Content, ContentStatus, ContentType
from xbot.models.session import Action, ActionStatus, ActionType, Session, SessionStatus
from xbot.persona import load_config
from xbot.persona.loader import load_persona
from xbot.safety.guard import SafetyGuard
from xbot.ai.trend_radar import fetch_rss_trends, fetch_multi_source_trends
from xbot.ai.trend_generator import generate_trend_take
import re




