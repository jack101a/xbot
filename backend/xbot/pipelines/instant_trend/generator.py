from __future__ import annotations

import logging
import re
from xbot.config import settings
from xbot.ai.anti_ai_gatekeeper import AntiAIGatekeeper
from xbot.ai.client import RoutingClient
from xbot.browser.actions.post_utils import smart_truncate_tweet_text
from xbot.pipelines.instant_trend.types import TrendCandidateTweet

logger = logging.getLogger(__name__)


async def generate_trend_commentary(
    topic: str,
    action_type: str,
    target_tweet: TrendCandidateTweet | None,
    persona_rules: list[str] | None = None,
    sentiment_tone: str = "balanced",
    ragebait_percentage: int = 0,
) -> str:
    """
    Generates punchy, human-like reaction or analysis to a trending topic or anchor tweet.
    Integrates official hashtags and media context from the source post while enforcing
    anti-AI gatekeeper constraints and specified tone (positive, negative, ragebait).
    """
    ai_client = RoutingClient()

    # Determine angle / tone
    is_ragebait = False
    if ragebait_percentage > 0:
        import random
        if random.randint(1, 100) <= ragebait_percentage:
            is_ragebait = True

    if is_ragebait or sentiment_tone == "ragebait":
        tone_guidance = "Angle: Take a spicy, unapologetic, debate-sparking contrarian angle that provokes replies and heated debate without violating platform rules."
    elif sentiment_tone == "positive":
        tone_guidance = "Angle: Enthusiastic, genuine excitement, hyped perspective."
    elif sentiment_tone == "negative":
        tone_guidance = "Angle: Critical, skeptical, questioning the creative/strategic direction."
    else:
        tone_guidance = "Angle: Sharp, witty observational perspective."

    # 1. Extract official source hashtags
    official_hashtags: list[str] = []
    if target_tweet:
        if target_tweet.hashtags:
            official_hashtags = [h for h in target_tweet.hashtags if len(h) > 2][:2]
        elif target_tweet.text:
            matches = list(dict.fromkeys(re.findall(r"#[A-Za-z0-9_]+", target_tweet.text)))
            official_hashtags = [m for m in matches if len(m) > 2][:2]

    # Fallback canonical hashtag from topic words if none extracted
    if not official_hashtags:
        topic_words = [w for w in re.findall(r"[A-Za-z0-9]+", topic) if len(w) > 2]
        if topic_words:
            official_hashtags = [f"#{topic_words[0].capitalize()}{topic_words[1].capitalize() if len(topic_words) > 1 else ''}"]

    hashtag_guidance = (
        f"Include the official hashtag from the source post: {' '.join(official_hashtags)} at the end."
        if official_hashtags
        else ""
    )

    # 2. Extract media context
    media_context = ""
    if target_tweet:
        if target_tweet.has_video:
            media_context = " [Source post contains video/trailer]"
        elif target_tweet.media_alts:
            media_context = f" [Source media: {target_tweet.media_alts[0][:80]}]"
        elif target_tweet.media_urls:
            media_context = " [Source post contains teaser/photo media]"

    rules_text = "\n".join(persona_rules or [
        "Be authentic, direct, and conversational.",
        "No corporate PR hype, no cringe marketing clichés, no em dashes.",
        "Keep total hashtags to 1-2 maximum (only official trend tags).",
    ])

    import datetime
    now_dt = datetime.datetime.now().astimezone()
    temporal_hint = f"Current Real-World Date: {now_dt.strftime('%A, %B %d, %Y')} (Active Calendar Year: {now_dt.year}). Grounding: Evaluate this trend in {now_dt.year}. Never assume or write that the year is 2024 or earlier.\n"


    if action_type == "quote" and target_tweet:
        prompt = (
            f"{temporal_hint}"
            f"You are reacting to a trending event on X: '{topic}'.\n"
            f"Specifically, you are QUOTE-TWEETING this post from @{target_tweet.author}{media_context}:\n"
            f"'''{target_tweet.text}'''\n\n"
            f"Write a sharp, high-engagement quote take (reaction, hot-take, or thoughtful insight).\n"
            f"{tone_guidance}\n"
            f"{hashtag_guidance}\n"
            f"Rules:\n{rules_text}\n"
            f"Keep it under 240 characters total. Output ONLY the quote tweet text."
        )
    else:
        context_hint = f" Context from top post from @{target_tweet.author}{media_context}: '{target_tweet.text[:150]}'" if target_tweet else ""
        prompt = (
            f"{temporal_hint}"
            f"You are posting about a trending event on X: '{topic}'.{context_hint}\n"
            f"Write an original, thoughtful observation or question to ignite discussion.\n"
            f"{tone_guidance}\n"
            f"{hashtag_guidance}\n"
            f"Rules:\n{rules_text}\n"
            f"Keep it under 250 characters total. Output ONLY the tweet text."
        )

    tag_suffix = f" {official_hashtags[0]}" if official_hashtags else ""
    fallback_text = (
        f"still taking in the {topic} news. curious to see how the community feels about this.{tag_suffix}"
        if action_type == "quote"
        else f"the discussion around {topic} is moving fast today. what's the general verdict?{tag_suffix}"
    )

    model_name = getattr(settings, "LITELLM_PRIMARY_MODEL", "gemini-3.1-flash-lite")
    try:
        response = await ai_client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": "You write engaging, authentic takes for X. You strictly avoid AI clichés and em dashes. You use official trend hashtags when appropriate."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.8,
            max_tokens=120,
        )
        raw_text = response.choices[0].message.content or ""
        clean_text = raw_text.strip().strip('"').strip("'")
    except Exception as e:
        logger.warning("InstantTrend: AI generation failed (%s), using fallback: %s", e, fallback_text)
        clean_text = fallback_text

    # Anti-AI Gatekeeper validation
    gatekeeper = AntiAIGatekeeper()
    validation = gatekeeper.validate(clean_text)
    if not validation.is_valid:
        logger.info("InstantTrend: Gatekeeper rejected take (%s), cleaning em-dashes and buzzwords...", validation.errors)
        clean_text = clean_text.replace("—", "-")
        for slop in ("delve", "testament", "tapestry", "game-changer", "buckle up"):
            clean_text = clean_text.replace(slop, "")

    # Ensure at least 1 official hashtag is preserved if space permits
    if official_hashtags:
        has_tag = any(ht.lower() in clean_text.lower() for ht in official_hashtags)
        if not has_tag:
            primary_tag = official_hashtags[0]
            if len(clean_text) + len(primary_tag) + 1 <= 260:
                clean_text = f"{clean_text.rstrip()} {primary_tag}"

    return smart_truncate_tweet_text(clean_text.strip(), 260)
