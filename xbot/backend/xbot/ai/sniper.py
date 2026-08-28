from __future__ import annotations

import json
import logging
import re
from typing import Any

from pydantic import BaseModel, Field

from xbot.ai.anti_ai_gatekeeper import strip_surrounding_quotes
from xbot.ai.client import get_ai_client
from xbot.ai.formatting_engine import (
    enforce_pacing_whitespace,
    strip_formulaic_trailing_emojis,
)

from xbot.config import settings
from xbot.persona.loader import Persona

logger = logging.getLogger(__name__)

VALID_ANGLES = {"contrarian", "framework", "question", "witty", "data", "insight"}
VALID_RESPONSE_MODES = {
    "pure_gif",
    "emoji_reaction",
    "punchy_one_liner",
    "witty_sarcasm",
    "casual_take",
    "in_depth_breakdown",
}

SNIPER_PROMPT_TEMPLATE = """=== HIGH-IMPACT SNIPER REPLY ARCHITECTURE (6 DYNAMIC MODALITIES) ===
Read the room, attached media, and top comments to select ONE of the following 6 response modes:

1. pure_gif:
   - Provide a targeted Tenor / X GIF search query in `gif_query` (e.g. 'side eye', 'popcorn eating', 'facepalm', 'mind blown', 'sweating nervous', 'tired sigh').
   - `reply_text` should be an optional ultra-short reaction (e.g. 'real', '💀', 'no notes', 'pure cinema', 'W') or empty/minimal.

2. emoji_reaction:
   - Ultra-short, authentic emoji reaction in `reply_text` (1-2 emojis max, e.g. 💀, 😭, 🔥, 🤌, 💯) when the room is purely reactive.
   - NO filler text.

3. punchy_one_liner:
   - Short conversational punch (20-90 chars) delivering immediate humor, dry agreement, or disbelief.
   - Examples: 'ok i agree', 'they are not gonna like this one', 'bro had 2 lines and dipped 💀', 'Rockstar is making a second life not a game 🔥'.

4. witty_sarcasm:
   - 1-2 sentences (50-160 chars) of dry humor, sarcastic observation, or relatable banter matching the comments.
   - Great for roasting bad takes, tech ironies, movie tropes, or shared community pain points.

5. casual_take:
   - Clear, grounded perspective or opinion (60-200 chars) without sounding like a textbook or lecture.
   - Conversational, human, authentic.

6. in_depth_breakdown:
   - 2-4 sentences (120-260 chars) of technical nuance, empirical data, or filmmaking/story analysis when the room calls for domain depth.

=== CRITICAL RULES (STRICT) ===
- STRICT CONTEXT ACCURACY: Talk directly and accurately about the exact subject, image, and discussion in the target tweet. NEVER force artificial analogies or unrelated hobbies.
- NO FORCED QUESTIONS: NEVER force your reply to end with a question mark ('?'). Only ask a question if your angle naturally calls for one. Statements, roasts, memes, and punchy takes should end with natural punctuation (. ! or none).
- NO FIXED LENGTH MINIMUMS: Ultra-short replies (1-30 chars) are 100% valid and encouraged for pure_gif, emoji_reaction, and punchy_one_liner modes.
- EMOJIS & HASHTAGS: Use natural, expressive emojis (💀, 😭, 🔥, 😂, 💯, 🤌, 🌴, 🎮) where fitting to express human emotion and timing. Include 1-2 relevant hashtags if natural for the topic (e.g. #GTA6, #Cinema, #DCU, #Tech).
- ZERO AI CLICHÉS: STRICTLY BANNED: delve, testament, tapestry, supercharge, beacon, plethora, moreover, furthermore, in conclusion, game-changer, leverage, multifaceted, pivotal, foster, vital, crucial, endeavor, Great post!, Awesome thread!
- NO INDIAN POLITICS: Zero references to Indian political parties or figures.
"""


class SniperResult(BaseModel):
    response_mode: str = Field(
        default="witty_sarcasm",
        description="Response mode: pure_gif, emoji_reaction, punchy_one_liner, witty_sarcasm, casual_take, in_depth_breakdown",
    )
    reply_text: str = Field(..., description="The drafted high-value reply text (natural length, sentence case)")
    debate_catalyst: str = Field(default="", description="Optional closing question or hook if asked")
    angle: str = Field(default="insight", description="The angle chosen: contrarian, framework, question, witty, data, or insight")
    angle_used: str | None = Field(default=None, description="Backwards compatibility alias for angle")
    gif_query: str | None = Field(default=None, description="Search term for Tenor/X GIF picker or None")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    reasoning: str = Field(default="", description="Brief explanation of the chosen response mode and angle")

    def __init__(self, **data: Any) -> None:
        if "reply_text" in data and isinstance(data["reply_text"], str):
            data["reply_text"] = strip_surrounding_quotes(data["reply_text"].strip())
        if "debate_catalyst" in data and isinstance(data["debate_catalyst"], str):
            data["debate_catalyst"] = strip_surrounding_quotes(data["debate_catalyst"].strip())

        if "response_mode" in data and isinstance(data["response_mode"], str):
            mode = data["response_mode"].strip().lower()
            data["response_mode"] = mode if mode in VALID_RESPONSE_MODES else "witty_sarcasm"
        else:
            data["response_mode"] = "witty_sarcasm"

        if "angle" in data and "angle_used" not in data:
            data["angle_used"] = data["angle"]
        elif "angle_used" in data and "angle" not in data:
            data["angle"] = data["angle_used"]
        elif "angle" not in data and "angle_used" not in data:
            data["angle"] = "insight"
            data["angle_used"] = "insight"

        if "debate_catalyst" not in data or not data["debate_catalyst"]:
            reply = data.get("reply_text", "")
            if reply:
                questions = re.findall(r'([^.!?\n]+\?)', reply)
                if questions:
                    data["debate_catalyst"] = questions[-1].strip()
                elif reply.strip().endswith("?"):
                    data["debate_catalyst"] = reply.strip()
                else:
                    data["debate_catalyst"] = ""
            else:
                data["debate_catalyst"] = ""
        super().__init__(**data)


# Backwards compatibility aliases
SniperReplyResult = SniperResult
DynamicReplyResult = SniperResult


def clean_text_for_json(text: str) -> str:
    """Clean markdown json wrappers from LLM output."""
    text = text.strip()
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()


def clean_raw_reply_text(text: str) -> str:
    """Cleans raw text output when JSON parsing fails."""
    text = clean_text_for_json(text).strip()
    text = re.sub(r'^(?:Reply|Draft|Tweet|Response):\s*', '', text, flags=re.IGNORECASE)
    text = strip_surrounding_quotes(text)
    return text.strip()


def _build_sniper_system_prompt(persona: Persona, preferred_angle: str | None = None) -> str:
    """Constructs the high-retention sniper system prompt supporting 6 dynamic modalities."""
    prompt_parts = [
        f"You are {persona.display_name} (@{persona.x_handle}). You are executing a high-impact Sniper Reply on X.",
        "Your goal is to draft an immediate, high-value, high-retention reply to a target Key Opinion Leader (KOL) post.",
        "You want your reply to command attention, earn organic engagement, and trigger replies from the author and audience.\n",
        "=== CHARACTER IDENTITY & VOICE ===",
        f"Background: {persona.identity.background}",
    ]

    if getattr(persona.identity, "occupation", None):
        prompt_parts.append(f"Occupation: {persona.identity.occupation}")

    prompt_parts.append(f"Personality Traits: {', '.join(persona.personality.traits)}")
    prompt_parts.append(f"Communication Style: {persona.personality.communication_style}")
    prompt_parts.append(f"Tone: {persona.writing_style.tone}")

    if persona.writing_style.formatting:
        prompt_parts.append("Formatting Rules:\n" + "\n".join(f"- {fmt}" for fmt in persona.writing_style.formatting))

    if persona.writing_style.examples:
        prompt_parts.append("Voice Examples:\n" + "\n".join(f"- \"{ex}\"" for ex in persona.writing_style.examples[:3]))

    if persona.interests.primary:
        prompt_parts.append(f"Primary Interests: {', '.join(persona.interests.primary)}")

    if persona.rules.always:
        prompt_parts.append("Always Rules:\n" + "\n".join(f"- {r}" for r in persona.rules.always))

    if persona.rules.never:
        prompt_parts.append("Never Rules:\n" + "\n".join(f"- {r}" for r in persona.rules.never))

    if getattr(persona, "system_prompt", None):
        prompt_parts.append("\n=== CUSTOM MASTER PROMPT ===")
        prompt_parts.append(persona.system_prompt)

    prompt_parts.append(f"\n{SNIPER_PROMPT_TEMPLATE}")

    prompt_parts.append(
        "\n=== X ALGORITHM & RETENTION OPTIMIZATION RULES ===\n"
        "1. STRICT TOPIC RELEVANCE (MANDATORY): You MUST directly address the EXACT topic, premise, claim, or joke of the target post. If the tweet is about tech, coding, AI, or startups, reply with witty commentary on tech/coding. If it is about cinema, talk about cinema. If it is about gaming/GTA, talk about gaming. NEVER bring up unrelated persona hobbies or forced metaphors.\n"
        "2. MATCH ENERGY & SCALE: Match the vibe of the room. Keep your reply sharp, authentic, and human.\n"
        "3. NO FORCED QUESTIONS: Deliver statements, one-liners, and roasts with conviction. Do NOT force a closing question mark unless you are genuinely asking a debate question.\n"
        "4. DYNAMIC HOOK OPENINGS & EMOTIONAL VARIETY: Vary your opening structure dynamically with genuine human emotion, humor, shock, or sarcasm:\n"
        "   - Sarcastic Banter: 'Bro had 2 lines in 2019 and dipped 💀', 'Rockstar is basically building a second life we have to pay $70 to enter 🔥'\n"
        "   - Shock & Hype: 'Masahide Fujii returning as Rocks is pure cinema. That laugh alone is carrying the entire arc 🔥'\n"
        "   - Dry Disbelief/Humor: 'The classic tired office worker vs coworker who makes HR mandatory dynamic 💀'\n"
        "   - Direct Punchy Observation: 'The draw distance alone is absurd. My GPU is sweating just looking at this 🌴'\n"
        "5. DYNAMIC NATURAL LENGTH: Allow short takes, witty roasts, or nuanced breakdowns (up to 260 chars).\n"
        "6. NATURAL EMOJIS & HASHTAGS: Use expressive emojis (💀, 😭, 🔥, 😂, 💯, 🤌, 🌴, 🎮) where fitting to express human emotion and timing. Include 1-2 relevant hashtags if natural for the topic (e.g. #GTA6, #Cinema, #DCU, #Tech).\n"
        "7. ZERO EXPENSIVE / FAKE ACADEMIC AI ENGLISH: STRICTLY BANNED: delve, tapestry, testament, supercharge, beacon, plethora, moreover, furthermore, in conclusion, game-changer, leverage, multifaceted, pivotal, foster, vital, crucial, endeavor. Speak in natural, grounded conversational voice.\n"
        "8. READ THE ROOM & POPULAR COMMENTS: Look at the tweet and top comments. If people are roasting or joking, join the banter with witty sarcasm. If it's a technical debate, bring empirical nuance.\n"
        "9. GIF / REACTION ATTACHMENT: For pure_gif mode or strong comedic timing/shock, provide a 1-3 word gif_query (e.g. 'side eye', 'facepalm', 'sweating nervous', 'tired sigh', 'this is fine fire', 'mind blown'). For analytical takes, return null.\n"
        "10. ABSOLUTE ZERO TOLERANCE FOR INDIAN POLITICS (HARD BAN): STRICTLY FORBIDDEN from discussing or mentioning Indian political parties or politicians.\n"
        "11. ANTI-BOT: NEVER use generic praise like 'Great post!', '100% agree!', 'Awesome thread!'. Stand out."
    )

    prompt_parts.append(
        "\n=== HIGH-IMPACT REPLY ANGLES ===\n"
        "- contrarian: Respectfully challenge the core premise with a crisp, logical counter-example or alternative viewpoint.\n"
        "- framework: Distill the topic into a concise, actionable mental model or 2-3 point framework.\n"
        "- question: Pose a deep, provocative technical dilemma that cuts straight to the trade-offs.\n"
        "- witty: Deliver a sharp, clever insider observation or relatable punchline.\n"
        "- data: Supply a concrete data point, metric, historical precedent, or empirical nuance.\n"
        "- insight: Provide profound domain depth, first-principles analysis, or unique tactical insight."
    )

    if preferred_angle and preferred_angle.lower() in VALID_ANGLES:
        prompt_parts.append(
            f"\nTARGET ANGLE: Use the '{preferred_angle.lower()}' angle for this reply."
        )
    else:
        prompt_parts.append(
            "\nTARGET ANGLE: Auto-select the most impactful angle among (contrarian, framework, question, witty, data, insight) "
            "that best matches your persona expertise and the target tweet content."
        )

    return "\n".join(prompt_parts)


def _detect_language_vibe(text: str, top_comments: list[Any]) -> str:
    """Detects whether the thread is Pure English or a Hinglish Mix based on vocabulary markers."""
    hinglish_markers = {
        "yaar", "bhai", "sahi", "mein", "nahi", "kya", "hai", "bhi", "toh", "arre",
        "karo", "hoga", "wala", "wali", "matlab", "alag", "kuch", "didi", "bhaiya",
        "sab", "bas", "par", "aur", "ek", "hum", "tum", "aaj", "kal", "kar", "raha",
        "rahi", "gaya", "gayi", "batao", "dekh", "sun", "apna", "apne", "sirf", "bol",
        "jugaad", "chal", "bhook", "neend", "paisa", "paise", "kaam", "zindagi"
    }

    all_text = text.lower()
    for tc in top_comments:
        c_str = tc.get("text", "") if isinstance(tc, dict) else str(tc)
        all_text += " " + c_str.lower()

    words = re.findall(r"\b[a-z]+\b", all_text)
    if not words:
        return "english"

    hinglish_hits = sum(1 for w in words if w in hinglish_markers)
    if hinglish_hits >= 2 or (hinglish_hits / max(1, len(words))) > 0.03:
        return "hinglish"
    return "english"


TECH_KEYWORDS = {
    "iphone", "macbook", "laptop", "smartphone", "android", "apple", "gpu", "nvidia",
    "intel", "amd", "snapdragon", "ai", "llm", "chatgpt", "claude", "deepseek", "openai",
    "anthropic", "coding", "developer", "software", "hardware", "battery", "benchmark",
    "saas", "tech", "gadget", "chip", "semiconductor", "google", "meta", "microsoft"
}

ANIME_KEYWORDS = {
    "one piece", "luffy", "zoro", "oda", "god valley", "manga", "anime", "powerscaling",
    "shonen", "naruto", "bleach", "jujutsu", "jjk", "demon slayer", "chapter", "spoilers",
    "toei", "dragon ball", "goku", "otaku", "cosplay", "sanji", "straw hat"
}

MOVIES_KEYWORDS = {
    "movie", "film", "cinema", "trailer", "box office", "actor", "director",
    "hollywood", "bollywood", "oscar", "streaming", "netflix", "hbo", "theatrical", "series"
}

GROWTH_KEYWORDS = {
    "drop your handle", "follow back", "mutuals", "f4f", "verified mutuals",
    "looking for mutuals", "follow everyone", "grow together", "drop handles"
}


def _build_sniper_user_prompt(target_tweet: dict[str, Any], preferred_angle: str | None = None) -> str:
    """Constructs the user prompt containing target tweet details, top comments, media descriptions, language directive, and schema instructions."""
    author = target_tweet.get("author") or target_tweet.get("handle") or target_tweet.get("author_handle") or "KOL"
    author = str(author).lstrip("@")
    text = target_tweet.get("text", "").strip()
    top_comments = target_tweet.get("top_comments") or target_tweet.get("replies_sample") or []

    lang_vibe = _detect_language_vibe(text, top_comments)
    if lang_vibe == "english":
        lang_instruction = (
            "LANGUAGE DIRECTIVE (STRICT): The target post and discussion are in English. "
            "DO NOT USE ANY HINDI OR HINGLISH WORDS (no 'yaar', 'bhai', 'sahi mein', 'arre', etc.). "
            "Respond in clean, natural, witty conversational English that sounds 100% human."
        )
    else:
        lang_instruction = (
            "LANGUAGE DIRECTIVE: The target post and comments contain a natural Hinglish mix. "
            "Respond in an authentic, natural blend of conversational English and subtle Hinglish "
            "(e.g. 'yaar', 'sahi mein', 'scene kya hai', 'fr', 'ngl')."
        )

    # Domain / Niche Lock Detection
    target_lower = text.lower()
    is_tech = any(k in target_lower for k in TECH_KEYWORDS)
    is_anime = any(k in target_lower for k in ANIME_KEYWORDS)
    is_movies = any(k in target_lower for k in MOVIES_KEYWORDS)
    is_growth = any(k in target_lower for k in GROWTH_KEYWORDS)

    if is_tech and not is_anime:
        domain_lock = (
            "🎯 DOMAIN LOCK (MANDATORY - TECH CONVERSATION):\n"
            "- The target post is strictly about TECHNOLOGY / HARDWARE / AI / COMPUTING.\n"
            "- YOUR REPLY MUST BE 100% ABOUT TECH.\n"
            "- STRICTLY FORBIDDEN: DO NOT mention anime, manga, One Piece, Oda, or unrelated pop culture!"
        )
    elif is_anime and not is_tech:
        domain_lock = (
            "🎯 DOMAIN LOCK (MANDATORY - ANIME / MANGA CONVERSATION):\n"
            "- The target post is strictly about ANIME / MANGA / ONE PIECE.\n"
            "- YOUR REPLY MUST BE 100% ABOUT ANIME & MANGA.\n"
            "- STRICTLY FORBIDDEN: DO NOT mention laptop chips, benchmarks, or coding!"
        )
    elif is_growth:
        domain_lock = (
            "🎯 DOMAIN LOCK (MANDATORY):\n"
            "- Reply naturally, casually, and concisely to this post without forcing self-introductions or artificial analogies."
        )
    elif is_movies:
        domain_lock = (
            "🎯 DOMAIN LOCK (MANDATORY - CINEMA & ENTERTAINMENT):\n"
            "- The target post is strictly about MOVIES / SHOWS / DIRECTING / BOX OFFICE.\n"
            "- Keep your response 100% grounded in cinema and filmmaking discussion."
        )
    else:
        domain_lock = (
            "🎯 DOMAIN LOCK (MANDATORY):\n"
            "- Reply ONLY to the exact topic and premise stated in the target post above."
        )

    prompt = (
        f"Draft a high-impact Sniper Reply to the following post by @{author}:\n\n"
        f"--- TARGET POST ---\n"
        f"Author: @{author}\n"
        f"Content: \"{text}\"\n"
    )

    if top_comments:
        prompt += "\n--- TOP COMMENTS IN THREAD (ROOM CONTEXT & SENTIMENT) ---\n"
        for i, tc in enumerate(top_comments[:10], 1):
            if isinstance(tc, dict):
                c_author = tc.get("author") or tc.get("handle") or tc.get("username") or ""
                c_author_str = f"@{str(c_author).lstrip('@')}: " if c_author else ""
                c_text = tc.get("text", "").strip()
                c_likes = tc.get("likes") or tc.get("like_count") or tc.get("favorites")
                c_likes_str = f" ({c_likes} likes)" if c_likes is not None else ""
                prompt += f"{i}. {c_author_str}\"{c_text}\"{c_likes_str}\n"
            else:
                prompt += f"{i}. \"{str(tc).strip()}\"\n"

    media_alts = target_tweet.get("media_alts") or []
    if media_alts:
        prompt += "\n--- ATTACHED IMAGE VISUAL DESCRIPTIONS ---\n"
        for i, alt in enumerate(media_alts, 1):
            prompt += f"- Image {i}: {alt}\n"

    prompt += "-------------------\n\n"
    prompt += f"{domain_lock}\n\n"
    prompt += f"{lang_instruction}\n\n"
    prompt += "Select the single best response_mode among (pure_gif, emoji_reaction, punchy_one_liner, witty_sarcasm, casual_take, in_depth_breakdown) that fits the context.\n"

    if preferred_angle and preferred_angle.lower() in VALID_ANGLES:
        prompt += f"Guide your response using the '{preferred_angle.lower()}' angle.\n"
    else:
        prompt += "Select the best angle: 'contrarian', 'framework', 'question', 'witty', 'data', or 'insight'.\n"

    prompt += (
        "\nReturn a JSON object with this exact schema:\n"
        "{\n"
        "  \"response_mode\": \"pure_gif | emoji_reaction | punchy_one_liner | witty_sarcasm | casual_take | in_depth_breakdown\",\n"
        "  \"reply_text\": \"Your complete reply text (natural length, sentence case, DO NOT force ? at the end unless asking a genuine question)\",\n"
        "  \"debate_catalyst\": \"Optional closing question extracted from reply_text if asked, otherwise empty string\",\n"
        "  \"angle\": \"contrarian | framework | question | witty | data | insight\",\n"
        "  \"gif_query\": \"Search keyword for GIF if response_mode is pure_gif or witty reaction fits; otherwise null\",\n"
        "  \"confidence\": 0.0-1.0,\n"
        "  \"reasoning\": \"Brief explanation of why the response_mode and angle fit the room vibe\"\n"
        "}\n"
        "Return ONLY the valid JSON object with no surrounding commentary."
    )
    return prompt


# 5-Stage Verification Gatekeeper Regex Patterns
BANNED_AI_WORDS_REGEX = re.compile(
    r"\b(delve|delving|tapestry|tapestries|testament|beacon|plethora|"
    r"moreover|furthermore|in conclusion|game[- ]?changer|leverage|leveraging|"
    r"multifaceted|pivotal|foster|fostering|vital|crucial|endeavor|endeavors|"
    r"supercharge|supercharged|supercharging|"
    r"realm|buckle up|let'?s dive in|unpacking|navigating the)\b",
    re.IGNORECASE,
)

BANNED_BOT_PRAISE_REGEX = re.compile(
    r"^(great (post|tweet|thread)|100% agree|awesome (post|thread)|"
    r"couldn'?t agree more|spot on|so true|well said)[!.]*",
    re.IGNORECASE,
)

BANNED_ROUTINE_FILLER_REGEX = re.compile(
    r"\b(my (morning|evening) (coffee|chai|tea)|sipping (my )?(chai|coffee)|"
    r"adrak chai|iced matcha|terrace sunset|peace is underrated|"
    r"just finished (my )?workout|in my gym gear|average day in)\b",
    re.IGNORECASE,
)

BANNED_ROBOTIC_QUESTIONS_REGEX = re.compile(
    r"\b(are you (trusting|ready for|excited for|holding onto|falling for|hyped for)|"
    r"what do you think|do you agree|what are your thoughts|let me know in the comments|"
    r"drop your thoughts|which side are you on)\b",
    re.IGNORECASE,
)

BANNED_POLITICS_REGEX = re.compile(
    r"\b(bjp|congress|aap|aam aadmi party|modi|narendra modi|rahul gandhi|"
    r"kejriwal|arvind kejriwal|amit shah|yogi|adityanath|hindutva|rss|"
    r"rashtriya swayamsevak|lok sabha|rajya sabha|bjp4india|incindia|"
    r"indian politics|indian election|mamata banerjee|samajwadi party|"
    r"bsp|dmk|aiadmk|shiv sena|trinamool)\b",
    re.IGNORECASE,
)


def verify_sniper_reply(
    reply_text: str,
    language_mode: str = "english",
    target_text: str | None = None,
    response_mode: str | None = None,
    gif_query: str | None = None,
) -> tuple[bool, str | None]:
    """
    Validates candidate reply against quality, safety, and domain-matching gatekeepers.
    Supports short replies, emoji reactions, and GIF queries without artificial length barriers.
    Returns (is_valid, failure_reason).
    """
    text = reply_text.strip()
    if response_mode == "pure_gif" and gif_query:
        pass
    elif not text:
        return False, "Empty reply text."

    # Stage 1: Length Constraint (No fixed minimums, maximum 280 chars)
    if len(text) > 280:
        return False, f"Length exceeds 280 characters ({len(text)} chars)."

    # Stage 2: Cliché & Negative Token Filters
    if BANNED_AI_WORDS_REGEX.search(text):
        m = BANNED_AI_WORDS_REGEX.search(text)
        return False, f"Contains banned AI academic word: '{m.group(0)}'."

    if BANNED_BOT_PRAISE_REGEX.search(text):
        return False, "Contains generic bot praise."

    if BANNED_ROUTINE_FILLER_REGEX.search(text):
        m = BANNED_ROUTINE_FILLER_REGEX.search(text)
        return False, f"Contains banned routine/beverage filler: '{m.group(0)}'."

    # Stage 3: Language Mode Adherence
    if language_mode == "english":
        hinglish_leak_markers = {"yaar", "bhai", "sahi", "mein", "kya", "hai", "arre", "matlab", "didi", "bhaiya"}
        words = set(re.findall(r"\b[a-z]+\b", text.lower()))
        leaks = words.intersection(hinglish_leak_markers)
        if leaks:
            return False, f"Language mode is Pure English but found Hindi words: {list(leaks)}."

    # Stage 4: Cross-Domain Contamination Gatekeeper
    if target_text:
        t_low = target_text.lower()
        r_low = text.lower()
        is_tech_target = any(k in t_low for k in TECH_KEYWORDS) and not any(k in t_low for k in ANIME_KEYWORDS)
        is_anime_target = any(k in t_low for k in ANIME_KEYWORDS) and not any(k in t_low for k in TECH_KEYWORDS)

        if is_tech_target:
            anime_contaminants = {"oda", "luffy", "zoro", "god valley", "anime", "manga", "powerscaling", "shonen", "chapter"}
            hits = [w for w in anime_contaminants if re.search(r"\b" + re.escape(w) + r"\b", r_low)]
            if hits:
                return False, f"Domain mismatch: Target post is tech, but reply contains anime keywords: {hits}."

        if is_anime_target:
            tech_contaminants = {"macbook", "gpu", "snapdragon", "m4 max", "benchmark", "nvidia", "intel", "semiconductor"}
            hits = [w for w in tech_contaminants if re.search(r"\b" + re.escape(w) + r"\b", r_low)]
            if hits:
                return False, f"Domain mismatch: Target post is anime, but reply contains tech hardware keywords: {hits}."

    # Stage 5: Banned Robotic Survey Questions Gatekeeper
    if BANNED_ROBOTIC_QUESTIONS_REGEX.search(text):
        m = BANNED_ROBOTIC_QUESTIONS_REGEX.search(text)
        return False, f"Contains robotic survey question: '{m.group(0)}'. Keep reply as a natural statement or banter."

    # Stage 6: Hard Indian Politics Blacklist
    if BANNED_POLITICS_REGEX.search(text):
        m = BANNED_POLITICS_REGEX.search(text)
        return False, f"Contains banned Indian political terms: '{m.group(0)}'."

    if target_text and BANNED_POLITICS_REGEX.search(target_text):
        return False, "Target post is related to Indian politics. Rejected by political safety filter."

    return True, None


async def generate_sniper_reply(
    persona: Persona,
    target_tweet: dict[str, Any],
    preferred_angle: str | None = None,
    opportunity_score: Any | None = None,
    client: Any | None = None,
) -> SniperResult:
    """
    Generates an algorithm-optimized, high-retention sniper reply supporting 6 modalities to a target KOL tweet.
    Uses persona voice, rules, room reading, and selected angle without forcing artificial question marks.
    Enforces verification with up to 2 retries.
    """
    author = target_tweet.get("author") or target_tweet.get("handle") or "creator"
    clean_author = str(author).lstrip("@")
    target_text = target_tweet.get("text", "")
    top_comments = target_tweet.get("top_comments") or []
    lang_mode = _detect_language_vibe(target_text, top_comments)

    system_prompt = _build_sniper_system_prompt(persona, preferred_angle)
    user_prompt = _build_sniper_user_prompt(target_tweet, preferred_angle)

    # Real-Time Web Search Fact-Grounding & Verification
    try:
        from xbot.ai.fact_grounder import ground_context_with_live_facts
        grounding_block = await ground_context_with_live_facts(target_text)
        if grounding_block:
            user_prompt += f"\n\n{grounding_block}"
    except Exception as g_err:
        logger.debug("Live fact grounding lookup skipped: %s", g_err)

    model = getattr(
        settings,
        "MODEL_REPLY_ANALYSIS",
        getattr(settings, "MODEL_GENERATION", getattr(settings, "MODEL_POST_CREATION", "gemini-3.5-flash-lite")),
    )

    ai_client = client if client is not None else get_ai_client()
    chosen_default_angle = preferred_angle.lower() if preferred_angle and preferred_angle.lower() in VALID_ANGLES else "insight"

    # Multimodal Vision Payload Construction if Images Exist
    media_urls = [u for u in target_tweet.get("media_urls", []) if isinstance(u, str) and u.startswith("http")]
    if media_urls:
        vision_user_content: list[dict[str, Any]] = [{"type": "text", "text": user_prompt}]
        for u in media_urls[:2]:
            vision_user_content.append({
                "type": "image_url",
                "image_url": {"url": u}
            })
    else:
        vision_user_content = user_prompt

    # 1. Attempt structured parse if supported by client
    try:
        if hasattr(ai_client, "beta") and hasattr(ai_client.beta, "chat") and hasattr(ai_client.beta.chat.completions, "parse"):
            completion = await ai_client.beta.chat.completions.parse(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_format=SniperResult,
            )
            parsed = completion.choices[0].message.parsed
            if isinstance(parsed, SniperResult):
                if len(parsed.reply_text) > 260:
                    parsed.reply_text = parsed.reply_text[:260].strip()
                parsed.reply_text = strip_surrounding_quotes(parsed.reply_text)
                return parsed
    except Exception as parse_err:
        logger.debug("Structured parse skipped/failed: %s", parse_err)

    # 2. Attempt standard completions with up to 3 retries and verification
    for attempt in range(3):
        try:
            try:
                completion = await ai_client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": vision_user_content},
                    ],
                    response_format={"type": "json_object"},
                )
            except Exception:
                completion = await ai_client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                )

            raw_content = completion.choices[0].message.content or ""
            if not isinstance(raw_content, str):
                raw_content = str(raw_content)

            cleaned_json = clean_text_for_json(raw_content)
            data = json.loads(cleaned_json)

            if isinstance(data, dict):
                if "reply" in data and isinstance(data["reply"], dict):
                    data = data["reply"]
                elif "content" in data and isinstance(data["content"], dict):
                    data = data["content"]

                reply_text = strip_surrounding_quotes(str(data.get("reply_text") or data.get("content") or "").strip())
                response_mode = str(data.get("response_mode") or "witty_sarcasm").lower().strip()
                if response_mode not in VALID_RESPONSE_MODES:
                    response_mode = "witty_sarcasm"

                debate_catalyst = strip_surrounding_quotes(str(data.get("debate_catalyst") or "").strip())
                angle_used = str(data.get("angle") or data.get("angle_used") or chosen_default_angle).lower()
                if angle_used not in VALID_ANGLES:
                    angle_used = chosen_default_angle
                confidence = float(data.get("confidence", 1.0))
                reasoning = str(data.get("reasoning") or "")

                raw_gif = data.get("gif_query")
                gif_query = None
                if raw_gif and str(raw_gif).strip().lower() not in ("null", "none", "", "n/a", "false"):
                    gif_query = str(raw_gif).strip()

                # Verification Check
                is_valid, fail_reason = verify_sniper_reply(
                    reply_text,
                    language_mode=lang_mode,
                    target_text=target_text,
                    response_mode=response_mode,
                    gif_query=gif_query,
                )
                if not is_valid and attempt < 2:
                    logger.warning("Sniper reply verification failed on attempt %d: %s. Retrying...", attempt + 1, fail_reason)
                    user_prompt += f"\n\nPREVIOUS GENERATION FAILED VERIFICATION: {fail_reason}. Please rewrite cleanly."
                    continue

                reply_text = strip_surrounding_quotes(reply_text)
                if response_mode not in ("emoji_reaction", "pure_gif"):
                    reply_text = strip_formulaic_trailing_emojis(reply_text)
                    reply_text = enforce_pacing_whitespace(reply_text)
                reply_text = strip_surrounding_quotes(reply_text)

                if len(reply_text) > 260:
                    reply_text = reply_text[:260].strip()

                return SniperResult(
                    response_mode=response_mode,
                    reply_text=reply_text,
                    debate_catalyst=debate_catalyst,
                    angle=angle_used,
                    angle_used=angle_used,
                    gif_query=gif_query,
                    confidence=confidence,
                    reasoning=reasoning,
                )
        except Exception as e:
            logger.warning("Attempt %d failed during sniper reply generation: %s", attempt + 1, e)

    # 3. Raw text fallback check
    if 'raw_content' in locals() and raw_content:
        cleaned_raw = clean_raw_reply_text(raw_content)
        if cleaned_raw:
            if len(cleaned_raw) > 260:
                cleaned_raw = cleaned_raw[:260].strip()
            cleaned_raw = strip_surrounding_quotes(cleaned_raw)
            return SniperResult(
                response_mode="casual_take",
                reply_text=cleaned_raw,
                angle=chosen_default_angle,
                angle_used=chosen_default_angle,
                confidence=0.8,
                reasoning="Fallback parsed from raw text completion",
            )

    # 4. If all models fail/timeout after retries, discard to avoid low-quality slop
    logger.warning("All top-tier writing models exhausted for @%s. Discarding reply to retry in next session.", clean_author)
    return SniperResult(
        response_mode="witty_sarcasm",
        reply_text="",
        debate_catalyst="",
        angle=chosen_default_angle,
        angle_used=chosen_default_angle,
        gif_query=None,
        confidence=0.0,
        reasoning=f"Generation failed: All top-tier writing models failed or timed out after retries for @{clean_author}. Discarded to prevent posting low-quality output.",
    )


class QuoteTakeResult(BaseModel):
    quote_text: str = Field(..., description="The drafted high-value standalone quote take")
    gif_query: str | None = Field(default=None, description="Search term for Tenor/X GIF picker or None")
    reasoning: str = Field(default="", description="Strategic rationale for the quote take")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    topic_understanding: str = Field(default="", description="Brief breakdown of what the target post and room are about")


async def generate_quote_take(
    persona: Persona,
    target_tweet: dict[str, Any],
    client: Any | None = None,
) -> QuoteTakeResult:
    """
    Generates a viral, high-signal Quote Tweet take tailored to the full root post,
    attached visual media descriptions, and top 10 liked comments in the thread.
    """
    author = target_tweet.get("author") or target_tweet.get("handle") or "Creator"
    author = str(author).lstrip("@")
    text = target_tweet.get("text", "").strip()
    media_alts = target_tweet.get("media_alts") or []
    top_comments = target_tweet.get("top_comments") or []

    comments_formatted = ""
    for ci, c in enumerate(top_comments[:10], 1):
        if isinstance(c, dict):
            c_author = c.get("author") or "user"
            c_text = c.get("text", "").strip()
            c_likes = c.get("likes") or 0
            comments_formatted += f"{ci}. @{c_author}: \"{c_text}\" ({c_likes} likes)\n"
        else:
            comments_formatted += f"{ci}. \"{str(c).strip()}\"\n"

    media_desc_str = ", ".join(media_alts) if media_alts else "Embedded image/video media"

    prompt = f"""You are an authentic, culturally savvy, high-IQ creator on X (Twitter) named {persona.display_name}.
You are analyzing this real live post to draft a viral, high-value QUOTE TWEET (standalone take adding a strong perspective).

=== TARGET TWEET ===
Author: @{author}
Content: "{text}"
Attached Media / Visual Details: {media_desc_str}

=== TOP 10 COMMENTS IN THE ROOM (SENTIMENT, HUMOR & DEBATE) ===
{comments_formatted if comments_formatted else 'No comments yet'}

=== GENERATION DIRECTIVES ===
1. 100% CONTEXT ACCURACY: Understand what the post, media, and room are actually discussing. Speak directly to the core topic. Never force bizarre analogies or unrelated persona hobbies.
2. HIGH-VALUE STANDALONE PERSPECTIVE: Deliver an insightful observation, witty comparison, or sharp industry take that adds genuine value to the timeline.
3. NATURAL HUMAN VOICE: Sound authentic, conversational, and observant.
4. EMOJIS & HASHTAGS: Use natural, expressive emojis (💀, 😭, 🔥, 😂, 💯, 🤌, 🌴, 🎮) where fitting. Include 1-2 relevant hashtags if natural for the topic (e.g. #GTA6, #Cinema, #DCU, #Tech).
5. GIF ATTACHMENT: Provide a 1-3 word Tenor search query in `gif_query` if a reaction GIF adds punch (e.g. 'mind blown', 'popcorn', 'sweating nervous', 'this is fine fire'); otherwise null.
6. LENGTH: Under 260 characters with clean natural punctuation (no cutting words in half).

Return ONLY a JSON object matching this schema:
{{
  "topic_understanding": "1-2 sentences explaining what the post, image, and room are discussing",
  "quote_text": "Your complete quote tweet take (natural length, sentence case)",
  "gif_query": "Tenor search query or null",
  "reasoning": "Brief explanation of why this perspective fits the topic"
}}
"""

    model = getattr(
        settings,
        "MODEL_REPLY_ANALYSIS",
        getattr(settings, "MODEL_GENERATION", getattr(settings, "MODEL_POST_CREATION", "gemini-3.5-flash-lite")),
    )
    ai_client = client if client is not None else get_ai_client()

    for attempt in range(3):
        try:
            resp = await ai_client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are a world-class social media strategist and authentic creator on X."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.75,
                max_tokens=600,
            )
            raw = resp.choices[0].message.content or ""
            clean_json = clean_text_for_json(raw)
            data = json.loads(clean_json)

            if isinstance(data, dict):
                quote_text = strip_surrounding_quotes(str(data.get("quote_text") or data.get("content") or "").strip())
                if len(quote_text) > 260:
                    quote_text = quote_text[:260].strip()

                raw_gif = data.get("gif_query")
                gif_query = None
                if raw_gif and str(raw_gif).strip().lower() not in ("null", "none", "", "n/a", "false"):
                    gif_query = str(raw_gif).strip()

                return QuoteTakeResult(
                    quote_text=quote_text,
                    gif_query=gif_query,
                    reasoning=str(data.get("reasoning") or ""),
                    topic_understanding=str(data.get("topic_understanding") or ""),
                    confidence=1.0,
                )
        except Exception as err:
            logger.warning("Attempt %d failed during quote take generation for @%s: %s", attempt + 1, author, err)

    # Fallback
    return QuoteTakeResult(
        quote_text=f"Sharp perspective on this from @{author}. Adding to the discussion.",
        gif_query=None,
        reasoning="Fallback quote take after retry exhaustion",
        confidence=0.5,
    )

