from __future__ import annotations

import datetime
import json
import logging
from typing import Any, Literal

from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from xbot.ai.anti_ai_gatekeeper import ANTI_AI_TYPOGRAPHY_DIRECTIVE
from xbot.ai.assembler import ContextAssembler
from xbot.ai.client import get_ai_client
from xbot.config import settings

logger = logging.getLogger(__name__)


class PlannedAction(BaseModel):
    type: Literal["post", "reply", "like", "retweet", "quote", "follow", "unfollow", "browse", "search", "scrape_trends", "scrape_metrics", "unfollow_non_followers", "follow_engagers", "poll", "thread"]
    target: str | None = Field(default=None, description="tweet_url, username, query, or null")
    content: str | None = Field(default=None, description="text content for post/reply/quote/thread root, null otherwise")
    thread_items: list[str] | None = Field(default=None, description="ordered list of tweet texts if composing a multi-tweet thread (2-6 tweets), or null")
    gif_query: str | None = Field(default=None, description="search keyword for reaction GIF if action warrants a GIF (e.g. 'side eye', 'chai sip', 'shocked', 'laughing'), or null")
    reasoning: str = Field(..., description="why this specific action is taken")
    priority: int = Field(..., description="execution priority (1 is highest)")


class SessionPlan(BaseModel):
    mood: str = Field(..., description="current mood/energy level")
    reasoning: str = Field(..., description="why these actions were chosen")
    actions: list[PlannedAction] = Field(default_factory=list, description="ordered list of actions to execute")
    skip_reason: str | None = Field(default=None, description="reason to skip session entirely, or null if executing")


class SessionPlanResponse(BaseModel):
    session_plan: SessionPlan


async def plan_session(
    db: AsyncSession,
    profile_slug: str,
    feed_snapshot: list[dict[str, Any]] | None = None,
    now_utc: datetime.datetime | None = None,
    token_budget: int = 4000,
    base_profile_dir: str = "/home/ubuntu/projects/xbot/data/profiles",
) -> SessionPlan:
    """
    Assembles context, constructs planning prompts, calls the primary LLM,
    and returns a validated SessionPlan.
    """
    if now_utc is None:
        now_utc = datetime.datetime.utcnow()

    # 1. Assemble context
    assembler = ContextAssembler(base_profile_dir=base_profile_dir)
    context = await assembler.assemble(
        db=db,
        profile_slug=profile_slug,
        now_utc=now_utc,
        token_budget=token_budget,
    )

    # 2. Format feed snapshot & Real-Time Web Search Fact Grounding
    feed_str = "No active feed snapshot available."
    if feed_snapshot:
        from xbot.ai.sniper import BANNED_POLITICS_REGEX
        feed_lines = []
        filtered_snapshot = [t for t in feed_snapshot if not BANNED_POLITICS_REGEX.search(t.get("text", ""))]
        for i, tweet in enumerate(filtered_snapshot[:20]):
            author = tweet.get("author", "unknown")
            text = tweet.get("text", "")
            likes = tweet.get("likes", 0)
            retweets = tweet.get("retweets", 0)
            replies = tweet.get("replies", 0)
            url = tweet.get("url", f"https://x.com/{author}/status/{i}")
            feed_lines.append(
                f"- Tweet {i+1}: by @{author} | URL: {url}\n"
                f"  Text: \"{text}\"\n"
                f"  Engagement: {likes} Likes, {retweets} Retweets, {replies} Replies"
            )
        feed_str = "\n".join(feed_lines)

        # Ground top trend/tweet with live web search facts
        try:
            from xbot.ai.fact_grounder import ground_context_with_live_facts
            if filtered_snapshot:
                top_candidate = filtered_snapshot[0].get("text", "")
                grounding_block = await ground_context_with_live_facts(top_candidate)
                if grounding_block:
                    feed_str = f"{grounding_block}\n\n## Live Community Timeline & Search Results\n{feed_str}"
        except Exception as g_err:
            logger.debug("Planner live fact grounding skipped: %s", g_err)

    # 3. Construct system and user prompts
    system_prompt = (
        f"You are {context.persona.display_name}. You are operating your X (Twitter) account: {context.persona.x_handle}.\n"
        f"You MUST act naturally and stay in character at all times. Here is your persona detail:\n\n"
        f"{context.persona_sheet}\n\n"
        f"{ANTI_AI_TYPOGRAPHY_DIRECTIVE}\n"
    )

    user_prompt = context.render_user_prompt(feed_snapshot_str=feed_str)
    user_prompt += (
        "\n\n## High-Growth Creator & Algorithm Action Instructions\n"
        "You are an organic growth engine on X. Flat, passive statements or posts written in a vacuum get zero views and zero engagement.\n"
        "Your actions MUST be driven by LIVE TRENDS, POPULAR DISCUSSIONS, and ACTIVE ENGAGEMENT in the feed snapshot:\n"
        "1. 🔍 TREND ANALYSIS & TOPIC SELECTION:\n"
        "   - DO NOT make up generic posts from scratch.\n"
        "   - Look at the live tweets and trending debates in `feed_snapshot` (One Piece chapter leaks, smartphone cameras/battery, Claude 3.7 vs ChatGPT o1, box office movies, follow-back trains).\n"
        "   - Synthesize your posts and polls to analyze, debate, or offer a contrarian take on these specific live trending discussions.\n"
        "2. 🎯 BALANCED ACTIVE ENGAGEMENT MIX:\n"
        "   - Plan 1-2 🎯 SNIPER REPLIES (type: 'reply'): Target MUST be a specific Twitter tweet status URL ('https://x.com/.../status/...'). NEVER use a news/RSS link or null target for replies!\n"
        "   - Plan 1 💬 QUOTE TWEET (type: 'quote'): Target MUST be a specific Twitter tweet status URL ('https://x.com/.../status/...'). ONLY quote viral, high-reach tweets with MINIMUM 100k views / impressions (100,000+ views). NEVER quote follow-for-follow (F4F) trains, mutuals parties, or engagement-growth posts — synthesize your own original high-value standalone posts from growth insights instead!\n"
        "   - Plan 1-2 ❤️ LIKES (type: 'like'): Target MUST be a specific Twitter tweet status URL ('https://x.com/.../status/...').\n"
        "   - Plan 1 👥 FOLLOW (type: 'follow') targeting an active Blue Tick peer username (prioritize Verified / Blue Tick creators and Indian community peers).\n"
        "   - Plan 1 ✍️ POST or POLL (type: 'post' or 'poll') analyzing the #1 most active debate or breaking news in the feed snapshot (target is null).\n"
        "3. ✍️ VIRAL POSTS, THREADS & POLLS FORMULA (AUTHENTIC HUMAN CREATOR VOICE):\n"
        "   - 💡 PERSONAL & RELATABLE PERSPECTIVE: Standalone posts MUST NOT read like a dry corporate review or detached Wikipedia summary. Frame the topic through YOUR PERSONAL EXPERIENCE, RELATABLE DILEMMAS, SELF-AWARE WIT, OR SPICY CREATOR CONVICTIONS!\n"
        "     * Example (Anime): 'Oda really dropped 15 straight chapters of peak lore only to hit us with a sudden break week right as the flashback was getting good. My emotional stability cannot handle this 😭'\n"
        "     * Example (Tech): 'Upgraded to a 144Hz OLED laptop to increase developer productivity and now I am just debugging runtime errors with unprecedented visual smoothness.'\n"
        "     * Example (AI): 'My toxic trait is opening 14 AI tabs to optimize a 10-line script that I could have written in 4 minutes by hand.'\n"
        "     * Example (Cinema): 'Watching a 3-hour IMAX epic and realizing halfway through that I drank a large iced latte right before the opening credits. A true battle of human willpower 🫠'\n"
        "   - 🧵 MULTI-TWEET THREADS (type: 'thread'): If breaking down a high-value insight, guide, or deep breakdown, set type='thread' with 'thread_items' (2 to 5 tweets):\n"
        "     * Tweet 1: Scroll-stopping hook with personal premise or provocative question ending in 🧵\n"
        "     * Tweets 2-(N-1): 1 concrete takeaway per tweet with line breaks and clean minimal bullets\n"
        "     * Tweet N: Takeaway summary + open engagement question asking for followers' experiences\n"
        "   - 🚫 ABSOLUTE ANTI-REPETITION MANDATE: Inspect the `Recently Created Posts & Drafts` and `Today's Actions` in your context. You are STRICTLY FORBIDDEN from posting, replying, or polling about any topic, angle, or tweet premise you have already covered today or recently. Rotate dynamically across your pillars (Anime -> Consumer Tech -> AI/Dev -> Cinema)!\n"
        "   - DYNAMIC LENGTH & CREATIVE FREEDOM: Never constrain yourself to a fixed formula or length. Posts and replies can be anything from a casual punchy reaction ('good 💯', 'nice', 'real', 'W', 'pure cinema 😭', or a single reaction GIF query), to a witty one-liner, to a 2-3 sentence take, to a multi-tweet thread. Give yourself space to think and adapt naturally to the vibe.\n"
        "   - 🚫 STRICT INDIAN POLITICS BAN: ABSOLUTELY NEVER post, poll, reply, like, or quote anything related to Indian politics (BJP, Congress, AAP, Modi, Rahul Gandhi, Kejriwal, Amit Shah, Yogi, elections, religious controversies). Keep all content 100% focused on Anime, Cinema/TV, Consumer Tech, and AI/Dev!\n"
        "   - EMOJI & CASING FREEDOM: Do NOT make it a fixed formula to end posts/replies with 1 emoji. At least 50% of your outputs should have ZERO emojis. Never use emojis as category labels (no 🍿, no 🤖). Let sharp text and observations speak for themselves.\n"
        "4. 🚫 ANTI-AI VOCABULARY: Never use academic AI buzzwords (delve, tapestry, testament, beacon, plethora, moreover, furthermore, in conclusion, game-changer, supercharge). Speak with authentic human creator voice.\n\n"
        "Return a valid JSON object matching this schema:\n"
        "{\n"
        "  \"session_plan\": {\n"
        "    \"mood\": \"current mood/energy level\",\n"
        "    \"reasoning\": \"overall rationale for chosen growth actions based on feed trends\",\n"
        "    \"actions\": [\n"
        "      {\n"
        "        \"type\": \"post | reply | like | retweet | quote | follow | unfollow | browse | search | scrape_trends | scrape_metrics | unfollow_non_followers | follow_engagers | poll | thread\",\n"
        "        \"target\": \"tweet_url or username or search_query or null. For follow_engagers, must be a tweet_url.\",\n"
        "        \"content\": \"content text if composing a post/reply/quote/thread root, null otherwise\",\n"
        "        \"thread_items\": [\"Tweet 1 hook\", \"Tweet 2 takeaway\", \"Tweet 3 closer\"] if type is thread, null otherwise,\n"
        "        \"gif_query\": \"null by default. Only specify a GIF search keyword if action warrants a GIF for comedic shock; otherwise null\",\n"
        "        \"reasoning\": \"why this specific action is taken for growth based on trend analysis\",\n"
        "        \"priority\": 1\n"
        "      }\n"
        "    ],\n"
        "    \"skip_reason\": \"optional string explaining why we should skip this session completely, or null\"\n"
        "  }\n"
        "}\n"
        "Return ONLY the valid JSON object, with no extra text."
    )



    # 4. Call LLM
    client = get_ai_client()
    planner_model = getattr(settings, "MODEL_PLANNER", settings.MODEL_TREND_ANALYSIS)
    try:
        # Attempt to use structured parsing if supported by primary model
        completion = await client.beta.chat.completions.parse(
            model=planner_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format=SessionPlanResponse,
            action_type="session_planner",
            profile_slug=profile_slug,
        )
        response_obj = completion.choices[0].message.parsed
        if response_obj and response_obj.session_plan:
            return response_obj.session_plan
        raise ValueError("Empty session plan parsed from LLM response.")
    except Exception as e:
        logger.warning(
            "OpenAI structured parsing failed (falling back to manual JSON parsing): %s",
            e,
        )

        # Fallback to standard chat completions
        completion = await client.chat.completions.create(
            model=planner_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            action_type="session_planner",
            profile_slug=profile_slug,
        )
        raw_text = completion.choices[0].message.content or ""

        # Preprocess in case markdown block surrounds it
        cleaned_text = raw_text.strip()
        if cleaned_text.startswith("```json"):
            cleaned_text = cleaned_text[7:]
        if cleaned_text.endswith("```"):
            cleaned_text = cleaned_text[:-3]
        cleaned_text = cleaned_text.strip()

        data = json.loads(cleaned_text)
        parsed_obj = SessionPlanResponse.model_validate(data)
        return parsed_obj.session_plan
