from __future__ import annotations

from xbot.ai.assembler import AssembledContext, ContextAssembler
from xbot.ai.engagement import EngagementDecision, EngagementEvaluator
from xbot.ai.generator import ContentGenerator, GeneratedContent
from xbot.ai.hook_optimizer import (
    HookCandidate,
    HookOptimizationResult,
    optimize_post_hook,
)
from xbot.ai.planner import PlannedAction, SessionPlan, plan_session
from xbot.ai.poll_generator import GeneratedPoll, generate_poll
from xbot.ai.post_session import PostSessionProcessor
from xbot.ai.sniper import SniperReplyResult, SniperResult, generate_sniper_reply
from xbot.ai.strategy import StrategyReviewer
from xbot.ai.trend_generator import TrendEvaluation, generate_trend_take
from xbot.ai.trend_radar import TrendItem, fetch_rss_trends

__all__ = [
    "AssembledContext",
    "ContextAssembler",
    "PlannedAction",
    "SessionPlan",
    "plan_session",
    "GeneratedContent",
    "ContentGenerator",
    "EngagementDecision",
    "EngagementEvaluator",
    "PostSessionProcessor",
    "SniperReplyResult",
    "SniperResult",
    "generate_sniper_reply",
    "StrategyReviewer",
    "HookCandidate",
    "HookOptimizationResult",
    "optimize_post_hook",
    "GeneratedPoll",
    "generate_poll",
    "TrendItem",
    "fetch_rss_trends",
    "TrendEvaluation",
    "generate_trend_take",
]

