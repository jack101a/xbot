from __future__ import annotations

import logging
import random
import re
from typing import Any

from xbot.persona.models import EntityStance, ExpressivenessConfig, LanguageConfig, Persona

logger = logging.getLogger(__name__)

# Devanagari Unicode block: \u0900-\u097F
DEVANAGARI_REGEX = re.compile(r"[\u0900-\u097F]")

# Common Romanized Hindi / Hinglish vocabulary markers
HINGLISH_MARKERS = {
    "yaar", "bhai", "sahi", "mein", "nahi", "kya", "hai", "bhi", "toh", "arre",
    "karo", "hoga", "wala", "wali", "matlab", "alag", "kuch", "didi", "bhaiya",
    "sab", "bas", "par", "aur", "ek", "hum", "tum", "aaj", "kal", "kar", "raha",
    "rahi", "gaya", "gayi", "batao", "dekh", "sun", "apna", "apne", "sirf", "bol",
    "jugaad", "chal", "bhook", "neend", "paisa", "paise", "kaam", "zindagi",
    "waise", "kahan", "kaise", "accha", "achha", "theek", "pagal", "bakwaas",
    "bindaas", "mast", "locha", "scene", "bawaal", "jhakaas", "chutiya", "bhaijaan",
    "desi", "angrezi", "lafda", "chalo", "shuru", "khatam", "solid"
}

# Alias dictionary for common pop-culture, cinema, anime, and tech entities
ENTITY_ALIASES: dict[str, list[str]] = {
    "christopher nolan": ["nolan", "oppenheimer", "interstellar", "tenet", "dunkirk", "dark knight"],
    "one piece": ["onepiece", "luffy", "zoro", "eiichiro oda", "oda", "straw hat", "strawhats", "egghead"],
    "apple": ["tim cook", "iphone", "macbook", "ios", "m3 max", "m4", "apple intelligence"],
    "corporate ai slop": ["ai slop", "linkedin influencers", "ai bubble", "prompt bros", "chatgpt wrappers"],
    "marvel": ["mcu", "marvel studios", "avengers", "kevin feige"],
    "sony playstation": ["playstation", "ps5", "sony interactive", "ps5 pro"],
    "cursor": ["cursor ai", "cursor editor", "anysphere"],
}


def detect_language_and_script(text: str, top_comments: list[Any] | None = None) -> dict[str, Any]:
    """
    Detects whether text and thread comments contain Devanagari Hindi, Romanized Hinglish,
    or pure English.
    """
    all_text = text or ""
    if top_comments:
        for tc in top_comments:
            c_str = tc.get("text", "") if isinstance(tc, dict) else str(tc)
            all_text += " " + c_str

    # 1. Check for Devanagari script characters
    devanagari_chars = len(DEVANAGARI_REGEX.findall(all_text))
    has_devanagari = devanagari_chars >= 3

    # 2. Check for Hinglish markers in Latin words
    words = re.findall(r"\b[a-zA-Z]+\b", all_text.lower())
    hinglish_hits = sum(1 for w in words if w in HINGLISH_MARKERS)
    total_words = max(1, len(words))
    has_hinglish = hinglish_hits >= 2 or (hinglish_hits / total_words) > 0.03

    if has_devanagari:
        dominant_vibe = "hindi_script"
    elif has_hinglish:
        dominant_vibe = "hinglish"
    else:
        dominant_vibe = "english"

    return {
        "has_devanagari": has_devanagari,
        "has_hinglish": has_hinglish,
        "devanagari_char_count": devanagari_chars,
        "hinglish_hit_count": hinglish_hits,
        "dominant_vibe": dominant_vibe,
    }


def match_entity_stances(text: str, persona: Persona) -> list[dict[str, Any]]:
    """
    Matches text against active entity stances in the persona.
    Resolves the active response orientation based on the stance's sentiment split ratio.
    """
    if not persona.stances:
        return []

    lower_text = text.lower()
    matched = []

    for stance in persona.stances:
        if not stance.is_active:
            continue

        stance_name_lower = stance.name.lower()
        # Direct name match
        is_match = stance_name_lower in lower_text

        # Alias match
        if not is_match:
            aliases = ENTITY_ALIASES.get(stance_name_lower, [])
            for alias in aliases:
                if re.search(r"\b" + re.escape(alias) + r"\b", lower_text):
                    is_match = True
                    break

        if is_match:
            # Weighted random selection based on sentiment_split
            split = stance.sentiment_split or {"praise": 60, "analysis": 30, "critique": 10}
            angles = list(split.keys())
            weights = [max(0, split.get(a, 0)) for a in angles]
            if sum(weights) == 0:
                weights = [1] * len(angles)

            selected_angle = random.choices(angles, weights=weights, k=1)[0]
            matched.append({
                "stance": stance,
                "selected_angle": selected_angle,
                "split": split,
            })

    return matched


def build_worldview_prompt_section(
    persona: Persona,
    context_text: str = "",
    top_comments: list[Any] | None = None,
    is_reply: bool = True,
) -> str:
    """
    Builds a high-impact prompt directive embedding:
    1. Active Entity Stances & Nuanced Ratio Angles (Idols vs Nemeses vs Nuanced Critics)
    2. Sociolinguistic Multilingual Code-Switching (English, Hinglish, Devanagari Hindi)
    3. Paralinguistic Emojis as Tone Markers (Irony, exhaustion, deadpan wit - strictly 0-2 max)
    """
    sections: list[str] = []

    # 1. ENTITY STANCES & WORLDVIEW ORIENTATION
    matched_stances = match_entity_stances(context_text, persona) if context_text else []
    lang_cfg: LanguageConfig = getattr(persona, "language_config", None) or LanguageConfig()
    exp_cfg: ExpressivenessConfig = getattr(persona, "expressiveness_config", None) or ExpressivenessConfig()

    stance_lines: list[str] = []
    if matched_stances:
        stance_lines.append("🎯 ACTIVE ENTITY STANCE DETECTED (MANDATORY WORLDVIEW ALIGNMENT):")
        for m in matched_stances:
            st: EntityStance = m["stance"]
            ang: str = m["selected_angle"]
            stance_lines.append(
                f"- Entity: '{st.name}' (Archetype: {st.archetype.upper()} | Category: {st.category})\n"
                f"  Active Response Angle for this post: **{ang.upper()}** (from configured split: {st.sentiment_split})\n"
                f"  Directive: {st.behavioral_rule or 'Adopt this stance with authentic creator nuance.'}"
            )
            if st.talking_points:
                stance_lines.append(f"  Key Themes to lean on: {', '.join(st.talking_points)}")

    if stance_lines:
        sections.append("\n".join(stance_lines))

    # 2. LINGUISTIC CODE-SWITCHING & DIALECT
    lang_detection = detect_language_and_script(context_text, top_comments)
    has_devanagari = lang_detection["has_devanagari"]
    has_hinglish = lang_detection["has_hinglish"]
    dominant = lang_detection["dominant_vibe"]

    lang_lines: list[str] = []
    lang_lines.append("🗣️ LINGUISTIC & CODE-SWITCHING DIRECTIVE:")

    if has_devanagari and lang_cfg.enable_hindi_script:
        lang_lines.append(
            "- The parent post / thread uses Devanagari Hindi script. You are fluent in Hindi.\n"
            "- You may reply in authentic, conversational Hindi (Devanagari script) or natural Hinglish.\n"
            "- Keep the tone natural, sharp, and culturally observant without formal textbook Hindi."
        )
    elif lang_cfg.enable_hinglish and (dominant == "hinglish" or lang_cfg.hinglish_mode == "full_bilingual" or (lang_cfg.hinglish_mode == "mirror_and_punchline" and has_hinglish)):
        register_note = {
            "urban_buff": "urban creator slang ('yaar', 'sahi mein', 'scene kya hai', 'legit', 'bhai')",
            "casual_desi": "casual street banter ('arre bhai', 'kya baat hai', 'matlab kuch bhi', 'bawaal')",
            "minimal": "subtle, rare tone markers ('yaar', 'sahi hai')"
        }.get(lang_cfg.slang_register, "natural urban Hinglish")

        lang_lines.append(
            f"- ROOM VIBE: Hinglish / conversational Indian creator context detected.\n"
            f"- REGISTER: Use {register_note}.\n"
            "- GOLDEN CODE-SWITCHING RULE (Narrative English + Evaluative Hinglish):\n"
            "  * State the technical setup, premise, or observation in crisp conversational English.\n"
            "  * Deliver the comedic punchline, emotional reaction, or ironic conclusion in natural Hinglish.\n"
            "  * Example: 'The camera hardware is flagship tier, par processing itna aggressive hai ki oil painting bana diya.'\n"
            "  * Never sound like a forced translation or corporate marketing bot."
        )
    else:
        lang_lines.append(
            "- The room / post is in English. Respond in crisp, natural, conversational English.\n"
            "- Do NOT inject random foreign words when the context is strictly English."
        )

    sections.append("\n".join(lang_lines))

    # 3. EXPRESSIVENESS, EMOJI GRAMMAR & MEDIA
    emoji_lines: list[str] = []
    emoji_lines.append("🎭 EMOJI GRAMMAR & VISUAL EXPRESSIVENESS:")
    if exp_cfg.emoji_mode == "none":
        emoji_lines.append("- STRICT ZERO EMOJIS: Do NOT use any emojis in this post.")
    else:
        emoji_lines.append(
            f"- EMOJIS ARE PARALINGUISTIC TONE MARKERS, NOT TOPIC ILLUSTRATIONS:\n"
            f"  * NEVER associate fixed emojis with categories (STRICT BAN on 🍿 for movies, 🤖 for tech, ⌚ for watches).\n"
            f"  * Use emojis solely for irony, sarcasm, exhaustion, deadpan humor, shock, or self-deprecation (e.g. 💀, 😭, 🫠, 👀, ✨, 🫡).\n"
            f"  * Maximum {exp_cfg.max_emojis} emoji(s) per response.\n"
            f"  * ZERO emojis is authentic and highly encouraged for dry, cynical, or analytical commentary.\n"
            f"  * Never use emojis as list bullets or predictable sentence terminators."
        )

    if is_reply:
        if exp_cfg.reply_meme_rate > 0:
            emoji_lines.append(
                f"- REACTION GIF/MEME ATTACHMENT ({exp_cfg.reply_meme_rate}% target):\n"
                "  If the reply has strong comedic timing, disbelief, or meme potential, return a 1-3 word `gif_query` (e.g. 'facepalm', 'side eye', 'mind blown'). If analytical or serious, return null."
            )
    else:
        if exp_cfg.thread_media_rate > 0:
            emoji_lines.append(
                f"- THREAD/POST VISUALS: Target visual media / stills ({exp_cfg.thread_media_rate}% rate) when breakdown benefits from graphic or movie frame context."
            )

    sections.append("\n".join(emoji_lines))

    return "\n\n".join(sections)
