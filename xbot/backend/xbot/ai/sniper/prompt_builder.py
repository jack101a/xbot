from __future__ import annotations
from .constants import *
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
from .evaluator import _detect_language_vibe

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
        "6. NATURAL EMOJIS (NO HASHTAGS IN REPLIES): Use expressive emojis (💀, 😭, 🔥, 😂, 💯, 🤌, 🌴, 🎮) where fitting to express human emotion and timing. NEVER use hashtags (#) in replies — hashtags look unnatural in reply threads.\n"
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

