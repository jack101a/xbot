"""
Centralized Master Character Prompt Engine.
Constructs the unified, top-of-prompt character identity, lived reality,
and dynamic boundaries for all generation pipelines (posts, replies, quotes, polls, visual posts).
Seamlessly syncs with all 6 sub-tabs of the Dashboard Persona Tab:
1. Identity & Voice (Name, Bio, Tone, Content Pillars, Short-Term Goals)
2. Reality & Boundaries (Owns, Never Owns, Expert In, Spectator Only, Never Claim)
3. Worldview & Stances (Entity Stances, Hinglish/Language config, Emoji config)
4. Topic Boundaries (Allowed Niche Topics, Strict Anti-Topics)
5. Daily Diary (Recent lived experience / log note)
6. Learned Memory (Adaptive habits, taboos, and writing patterns from memory bank)
"""

from __future__ import annotations

import datetime
from pathlib import Path
from typing import Any, Optional
from xbot.config import settings
from xbot.persona.models import Persona, LearnedState


BANNED_AI_WORDS = [
    "delve", "tapestry", "testament", "supercharge", "plethora", "moreover",
    "furthermore", "in conclusion", "game-changer", "leverage", "multifaceted",
    "pivotal", "foster", "vital", "crucial", "robust", "facilitate", "bespoke"
]


def build_character_master_prompt(
    persona: Persona,
    action_type: str | None = None,
    profile_dir: Path | str | None = None,
    learned_state: Optional[LearnedState] = None,
) -> str:
    """
    Builds the clean, unified, top-of-prompt character identity and boundary anchor.
    This prompt contains NO hardcoded character limits and NO developer/GPU hallucinations.
    All boundaries, possessions, stances, goals, and interests are dynamically loaded 
    from the persona configuration and dashboard settings.
    """
    now_dt = datetime.datetime.now().astimezone()
    date_str = now_dt.strftime("%A, %B %d, %Y")
    year_str = str(now_dt.year)

    display_name = persona.display_name or "Creator"
    handle = (persona.x_handle or "creator").lstrip("@")
    
    # -------------------------------------------------------------
    # 1. Identity & Demographics
    # -------------------------------------------------------------
    identity = getattr(persona, "identity", None)
    background = getattr(identity, "background", "") if identity else ""
    age = getattr(identity, "age", None) if identity else None
    location = getattr(identity, "location", None) if identity else None
    education = getattr(identity, "education", None) if identity else None
    occupation = getattr(identity, "occupation", None) if identity else None

    # -------------------------------------------------------------
    # 2. Personality, Voice & Goals
    # -------------------------------------------------------------
    personality = getattr(persona, "personality", None)
    comm_style = getattr(personality, "communication_style", "Sharp, witty, culturally observant, and conversational") if personality else "Sharp, witty, culturally observant, and conversational"
    writing_style = getattr(persona, "writing_style", None)
    tone = getattr(writing_style, "tone", "Witty, conversational, personal, culturally fluent") if writing_style else "Witty, conversational, personal, culturally fluent"

    goals = getattr(persona, "goals", None)
    content_pillars = getattr(goals, "content_pillars", []) if goals else []
    short_term_goals = getattr(goals, "short_term", []) if goals else []

    # -------------------------------------------------------------
    # 3. Dynamic Boundaries
    # -------------------------------------------------------------
    boundaries = getattr(persona, "boundaries", None)
    owns = getattr(boundaries, "owns", []) if boundaries else []
    never_owns = getattr(boundaries, "never_owns", []) if boundaries else []
    expert_in = getattr(boundaries, "expert_in", []) if boundaries else []
    spectator_only = getattr(boundaries, "spectator_only", []) if boundaries else []
    never_claim_to_be = getattr(boundaries, "never_claim_to_be", []) if boundaries else []

    # -------------------------------------------------------------
    # 4. Worldview, Stances, Language & Expressiveness
    # -------------------------------------------------------------
    stances = [s for s in getattr(persona, "stances", []) if getattr(s, "is_active", True)]
    lang_cfg = getattr(persona, "language_config", None)
    exp_cfg = getattr(persona, "expressiveness_config", None)

    # -------------------------------------------------------------
    # 5. Topic Boundaries (Allowed vs Anti-Topics)
    # -------------------------------------------------------------
    interests = getattr(persona, "interests", None)
    primary_interests = getattr(interests, "primary", []) if interests else []
    will_not_discuss = getattr(interests, "will_not_discuss", []) if interests else []

    likes = getattr(persona, "likes", None)
    dislikes = getattr(persona, "dislikes", None)

    # -------------------------------------------------------------
    # 6. Profile Directory, Learned Memory & Diary Integration
    # -------------------------------------------------------------
    if profile_dir is None and getattr(persona, "id", None):
        base_dir = getattr(settings, "BASE_PROFILE_DIR", "/srv/ajaxhs/config/xbot/profiles")
        candidate = Path(base_dir) / persona.id
        if candidate.exists():
            profile_dir = candidate
        else:
            # Fallback to local workspace data/profiles
            local_cand = Path(__file__).resolve().parents[3] / "data" / "profiles" / persona.id
            if local_cand.exists():
                profile_dir = local_cand

    if learned_state is None and profile_dir:
        from xbot.persona.loader import load_learned_state
        try:
            learned_state = load_learned_state(Path(profile_dir))
        except Exception:
            learned_state = None

    recent_diary_snippet = None
    if profile_dir:
        diary_dir = Path(profile_dir) / "diary"
        if diary_dir.exists():
            entries = sorted(diary_dir.glob("*.md"), reverse=True)
            if entries:
                try:
                    text = entries[0].read_text(encoding="utf-8")
                    content_lines = [
                        line.strip() for line in text.splitlines()
                        if line.strip() and not line.startswith("#") and not line.startswith("**Mood")
                    ]
                    if content_lines:
                        recent_diary_snippet = " ".join(content_lines[:2])[:180]
                except Exception:
                    pass

    # -------------------------------------------------------------
    # Assemble Clean Master Prompt
    # -------------------------------------------------------------
    lines = [
        f"You are {display_name} (@{handle}), an authentic creator posting live on X (Twitter).",
        f"Current Date: {date_str} (Year: {year_str}). You are active in {year_str}.",
    ]

    # Demographic Bio Line
    bio_details = []
    if age:
        bio_details.append(f"Age: {age}")
    if location:
        bio_details.append(f"Location: {location}")
    if education:
        bio_details.append(f"Education: {education}")
    if occupation:
        bio_details.append(f"Occupation: {occupation}")

    clean_background = background
    if clean_background:
        import re
        clean_background = re.sub(r'\b(?:adult\s+)?(?:woman|female|man|male|girl|boy)\b', 'creator', clean_background, flags=re.IGNORECASE)

    if bio_details or clean_background:
        bio_summary = " | ".join(bio_details)
        lines.append(f"Profile Bio: {clean_background}" + (f" ({bio_summary})" if bio_summary else ""))

    # Voice & Cadence
    voice_bullets = [
        f"- Style & Tone: {comm_style}. {tone}.",
        "- Cadence: Natural, conversational human pacing. Speak like a real person scrolling on their phone, never an essayist.",
        "- Subjectivity: Express opinions as personal human reactions ('honestly feels like', 'the wild part is', 'not sure if it's just me', 'I respect it'), never cold encyclopedic lectures.",
    ]
    if content_pillars:
        clean_pillars = "; ".join(content_pillars[:4])
        voice_bullets.append(f"- Content Pillars: {clean_pillars}.")
    if short_term_goals:
        clean_goals = "; ".join(short_term_goals[:2])
        voice_bullets.append(f"- Current Focus: {clean_goals}.")

    # Language & Code-switching
    if lang_cfg and getattr(lang_cfg, "enable_hinglish", False):
        register = getattr(lang_cfg, "slang_register", "urban_buff")
        slang_desc = "yaar, scene, legit, sahi mein" if register == "urban_buff" else "bhai, arre, subtle desi nuance"
        voice_bullets.append(
            f"- Language & Register: Natural conversational English with contextual Hinglish code-switching ({slang_desc}) when culturally fitting."
        )

    lines.extend(["", "VOICE & CADENCE:"] + voice_bullets)

    # Dynamic Character Reality & Boundaries
    owns_str = ", ".join(owns) if owns else "Everyday smartphone, laptop for media editing/working"
    never_owns_str = ", ".join(never_owns) if never_owns else "Dedicated GPUs, server clusters, Linux dev rigs, crypto rigs"
    expert_in_str = ", ".join(expert_in) if expert_in else "Media aesthetics, visual storytelling, pop culture"
    spectator_only_str = ", ".join(spectator_only) if spectator_only else "Software coding, hardware silicon, enterprise servers"
    never_claim_to_be_str = ", ".join(never_claim_to_be) if never_claim_to_be else "Software developer, programmer, tech founder"

    lines.extend([
        "",
        "CHARACTER REALITY & BOUNDARIES (ENFORCE STRICTLY):",
        f"- What you own & use: {owns_str}.",
        f"- NEVER claim to own: {never_owns_str}.",
        f"- Deep knowledge & skills: {expert_in_str}.",
        f"- Zero expertise / Spectator only: {spectator_only_str}.",
        "  *(On these topics, react ONLY as a curious observer, everyday consumer, or casual spectator. NEVER act like an expert).* ",
        f"- Roles you are NOT: {never_claim_to_be_str}.",
        "  *(NEVER claim to have these jobs, degrees, or professional backgrounds).*",
        "- GENDER NEUTRALITY (MANDATORY): NEVER disclose, admit, or specify whether you are male or female. You are strictly a creator. NEVER say 'as a guy/girl/man/woman', 'bro', 'sis'. In Hindi/Hinglish, NEVER use gender-specific verb inflections (avoid 'chahti hoon' / 'chahta hoon', 'karungi' / 'karunga', 'rahi hoon' / 'raha hoon'). Always use gender-neutral phrasing ('connect karte hain', 'karna hai', 'lagta hai', 'sochte hain').",
    ])

    # Worldview & Entity Stances (from Dashboard Stances Editor)
    if stances:
        stance_entries = []
        for st in stances[:5]:
            rule = getattr(st, "behavioral_rule", "").strip()
            if rule:
                stance_entries.append(f"- {st.name}: {rule}")
            else:
                stance_entries.append(f"- {st.name} ({st.archetype}): Category: {st.category}")
        lines.extend(["", "WORLDVIEW & ENTITY STANCES:"] + stance_entries)

    # Dynamic Topic Boundaries (from Dashboard Topics Editor)
    primary_interests_str = "; ".join(primary_interests) if primary_interests else "Cinema, consumer tech, pop culture"
    will_not_discuss_str = "; ".join(will_not_discuss) if will_not_discuss else "Electoral politics, communal disputes"

    lines.extend([
        "",
        "DYNAMIC TOPIC BOUNDARIES (FROM DASHBOARD):",
        f"- Allowed Niche Topics: {primary_interests_str}.",
        f"- Strict Anti-Topics to Avoid: {will_not_discuss_str}.",
    ])

    # Learned Cognitive Memory (from Dashboard Learned Memory Tab / learned_state.yaml)
    if learned_state:
        memory_bullets = []
        chars = getattr(learned_state, "characteristics", None)
        if chars and getattr(chars, "behavioral_adaptations", None):
            for a in chars.behavioral_adaptations[:2]:
                memory_bullets.append(f"- Adaptive Mindset: {a.strip()}")

        habits = getattr(learned_state, "habits", None)
        if habits and getattr(habits, "learned_writing_patterns", None):
            for p in habits.learned_writing_patterns[:2]:
                memory_bullets.append(f"- Voice Nuance: {p.strip()}")

        dislikes_learned = getattr(learned_state, "dislikes", None)
        if dislikes_learned and getattr(dislikes_learned, "learned_taboos", None):
            for t in dislikes_learned.learned_taboos[:2]:
                memory_bullets.append(f"- Learned Taboo: {t.strip()}")

        if memory_bullets:
            lines.extend(["", "LEARNED COGNITIVE MEMORY:"] + memory_bullets)

    # Recent Diary Lived Experience (from Dashboard Daily Diary)
    if recent_diary_snippet:
        lines.extend([
            "",
            "RECENT LIVED CONTEXT (DAILY DIARY):",
            f"- Grounded Experience: {recent_diary_snippet}...",
        ])

    # Anti-AI Quality Rules & Dynamic Emoji Caps
    max_emojis = getattr(exp_cfg, "max_emojis", 2) if exp_cfg else 2
    banned_str = ", ".join(BANNED_AI_WORDS)
    lines.extend([
        "",
        "ANTI-AI QUALITY RULES:",
        f"- BANNED VOCABULARY: Do not use {banned_str}.",
        f"- EMOJIS: 0-{max_emojis} contextual tone markers max (e.g. 😭, 💀, 👀, 🫠). Zero emojis is completely fine. NEVER use topic-label emojis (no 🍿 for cinema, 🤖 for tech).",
        "- NO HASHTAGS IN REPLIES: Never use hashtags in replies or quote tweets.",
        "- STRICT GENDER NEUTRALITY: Never state or imply male or female in any post, reply, or quote. Zero gendered self-references.",
    ])

    return "\n".join(lines)
