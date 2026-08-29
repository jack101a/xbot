from __future__ import annotations

from xbot.ai.assembler import AssembledContext, ContextAssembler
from xbot.ai.engagement import EngagementDecision, EngagementEvaluator
from xbot.ai.generator import ContentGenerator, GeneratedContent
from xbot.ai.hook_optimizer import (
    HookCandidate,
    HookOptimizationResult,
    OptimizedPostResult,
    calculate_bookmark_score,
    extract_links,
    optimize_post_for_virality,
    optimize_post_hook,
)
from xbot.ai.planner import PlannedAction, SessionPlan, plan_session
from xbot.ai.poll_generator import GeneratedPoll, generate_poll
from xbot.ai.post_session import PostSessionProcessor
from xbot.ai.post_synthesizer import SynthesizedPostResult, synthesize_creator_post
from xbot.ai.sniper import SniperResult, generate_sniper_reply
from xbot.ai.strategy import StrategyReviewer
from xbot.ai.growth_scorer import (
    OpportunityScore,
    is_f4f_or_engagement_growth_post,
    score_tweet_opportunity,
)
from xbot.ai.formatting_engine import (
    ARCHETYPE_REGISTRY,
    PostFormattingArchetype,
    format_content,
    post_process_formatted_content,
    select_archetype,
)
from xbot.ai.trend_generator import TrendEvaluation, generate_trend_take

from xbot.ai.nvidia_image import (
    NVIDIA_MODELS,
    build_nvidia_payload,
    extract_image_from_response,
    generate_and_save_nvidia_image_async,
    generate_nvidia_image_async,
    snap_flux_dimension,
)
from xbot.ai.x_researcher import (
    DownloadedMedia,
    TopicResearchReport,
    ViralTweet,
    research_topic_comprehensively,
)

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
    "OptimizedPostResult",
    "optimize_post_for_virality",
    "extract_links",
    "calculate_bookmark_score",
    "SynthesizedPostResult",
    "synthesize_creator_post",
    "GeneratedPoll",
    "generate_poll",
    "OpportunityScore",
    "score_tweet_opportunity",
    "is_f4f_or_engagement_growth_post",
    "TrendItem",
    "fetch_rss_trends",
    "TrendEvaluation",
    "generate_trend_take",
    "VisualPostSpec",
    "generate_visual_post_spec",
    "GeneratedThreadResponse",
    "generate_thread",
    "PostFormattingArchetype",
    "format_content",
    "select_archetype",
    "post_process_formatted_content",
    "TopicResearchReport",
    "ViralTweet",
    "DownloadedMedia",
    "research_topic_comprehensively",
    "generate_nvidia_image_async",
    "generate_and_save_nvidia_image_async",
    "NVIDIA_MODELS",
    "snap_flux_dimension",
]


