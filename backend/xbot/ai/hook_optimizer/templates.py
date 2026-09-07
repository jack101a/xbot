from __future__ import annotations
import json
import logging
import re
from typing import Any, Literal
from pydantic import BaseModel, Field, field_validator
from xbot.ai.anti_ai_gatekeeper import strip_surrounding_quotes
from xbot.ai.client import get_ai_client
from xbot.config import settings
from .scorer import _get_persona_field

def _build_hook_optimizer_system_prompt(persona: Any, topic: str = "") -> str:
    """Builds the viral hook generation and evaluation system prompt."""
    display_name = _get_persona_field(persona, "display_name", default="Autonomous Creator")
    x_handle = _get_persona_field(persona, "x_handle", default="creator")
    background = _get_persona_field(persona, "identity", "background", default="")
    occupation = _get_persona_field(persona, "identity", "occupation", default="")
    traits = _get_persona_field(persona, "personality", "traits", default=[])
    comm_style = _get_persona_field(persona, "personality", "communication_style", default="")
    tone = _get_persona_field(persona, "writing_style", "tone", default="sharp, authentic")
    formatting = _get_persona_field(persona, "writing_style", "formatting", default=[])
    examples = _get_persona_field(persona, "writing_style", "examples", default=[])
    always_rules = _get_persona_field(persona, "rules", "always", default=[])
    never_rules = _get_persona_field(persona, "rules", "never", default=[])
    system_prompt = _get_persona_field(persona, "system_prompt", default="")

    prompt_parts = [
        f"You are {display_name} (@{x_handle}). You are an elite X (Twitter) copywriter and viral hook optimizer.",
        "Your mission is to generate and rigorously score 4 scroll-stopping opening hooks for a post draft.",
        "The opening hook determines 90% of feed retention and dwell time.\n",
        "=== CHARACTER IDENTITY & VOICE ===",
    ]

    if background:
        prompt_parts.append(f"Background: {background}")
    if occupation:
        prompt_parts.append(f"Occupation: {occupation}")
    if traits:
        prompt_parts.append(f"Personality Traits: {', '.join(traits)}")
    if comm_style:
        prompt_parts.append(f"Communication Style: {comm_style}")
    if tone:
        prompt_parts.append(f"Tone: {tone}")
    if formatting:
        prompt_parts.append("Formatting Rules:\n" + "\n".join(f"- {fmt}" for fmt in formatting))
    if examples:
        prompt_parts.append("Voice Examples:\n" + "\n".join(f"- \"{ex}\"" for ex in examples[:3]))
    if always_rules:
        prompt_parts.append("Always Rules:\n" + "\n".join(f"- {r}" for r in always_rules))
    if never_rules:
        prompt_parts.append("Never Rules:\n" + "\n".join(f"- {r}" for r in never_rules))
    if system_prompt:
        prompt_parts.append(f"\n=== CUSTOM MASTER PROMPT ===\n{system_prompt}")

    prompt_parts.append(
        "\n=== 6 VIRAL HOOK ARCHETYPES (REQUIRED) ===\n"
        "1. curiosity_gap: Creates an irresistible information gap or provocative mystery that forces the reader to stop scrolling.\n"
        "2. contrarian: Directly challenges conventional wisdom, industry dogma, or common consensus with a sharp counter-intuitive claim.\n"
        "3. framework_breakdown: Promises a distilled, actionable mental model, taxonomy, or high-density tactical teardown.\n"
        "4. story_relatable: Opens with an immediate, gritty, first-person narrative hook or battle-tested real-world scenario.\n"
        "5. statistical_data: Leads with a startling metric, quantitative comparison, or empirical data point.\n"
        "6. bold_prediction: Makes a polarizing, high-conviction forecast or forward-looking industry stake."
    )

    prompt_parts.append(
        "\n=== RETENTION & QUALITY EVALUATION CRITERIA ===\n"
        "1. SCROLL-STOPPING INTRIGUE: The first line must instantly capture attention in a fast-moving feed.\n"
        "2. ZERO AI FLUFF & CLICHÉS: STRICTLY FORBIDDEN: 'Let's dive in', 'In this thread', 'Unpack', 'Mastering', 'Game-changer', 'Delve', 'Here is why', 'Buckle up', 'Today I want to share', or generic rhetorical openers.\n"
        "3. BREVITY: Hook text MUST be strictly under 140 characters (<140 chars) to avoid 'Show more' truncation on mobile.\n"
        "4. NO HASHTAGS: Never include hashtags (#) in the hook.\n"
        "5. SCORING (1.0 to 10.0): Evaluate each hook on expected dwell time, scroll-stopping power, and persona alignment."
    )

    if topic:
        prompt_parts.append(f"\nFOCUS TOPIC: {topic}")

    return "\n".join(prompt_parts)

def _build_hook_optimizer_user_prompt(draft_content: str, topic: str = "") -> str:
    """Builds the user prompt for hook optimization."""
    topic_str = f"Topic / Context: {topic}\n" if topic else ""
    return (
        f"{topic_str}"
        f"Original Post Draft:\n"
        f"\"\"\"\n{draft_content}\n\"\"\"\n\n"
        f"Generate exactly 6 hook candidates (one for each archetype: curiosity_gap, contrarian, framework_breakdown, story_relatable, statistical_data, bold_prediction).\n"
        f"Evaluate and score each hook from 1.0 to 10.0 based on scroll-stopping power and dwell retention.\n\n"
        f"Return a JSON object with this exact schema:\n"
        f"{{\n"
        f"  \"candidates\": [\n"
        f"    {{\n"
        f"      \"archetype\": \"curiosity_gap\",\n"
        f"      \"hook_text\": \"Opening hook text under 140 chars\",\n"
        f"      \"score\": 8.5,\n"
        f"      \"reasoning\": \"Why this hook creates high curiosity and dwell retention\"\n"
        f"    }},\n"
        f"    {{\n"
        f"      \"archetype\": \"contrarian\",\n"
        f"      \"hook_text\": \"Sharp counter-intuitive hook text\",\n"
        f"      \"score\": 9.2,\n"
        f"      \"reasoning\": \"Why this contrarian angle stops the scroll\"\n"
        f"    }},\n"
        f"    {{\n"
        f"      \"archetype\": \"framework_breakdown\",\n"
        f"      \"hook_text\": \"Distilled tactical framework hook text\",\n"
        f"      \"score\": 8.0,\n"
        f"      \"reasoning\": \"Why this framework hook promises high value\"\n"
        f"    }},\n"
        f"    {{\n"
        f"      \"archetype\": \"story_relatable\",\n"
        f"      \"hook_text\": \"Relatable first-person war story hook text\",\n"
        f"      \"score\": 8.7,\n"
        f"      \"reasoning\": \"Why this story hook triggers empathy and engagement\"\n"
        f"    }},\n"
        f"    {{\n"
        f"      \"archetype\": \"statistical_data\",\n"
        f"      \"hook_text\": \"Punchy data-backed opening hook text\",\n"
        f"      \"score\": 8.4,\n"
        f"      \"reasoning\": \"Why hard data immediately establishes authority\"\n"
        f"    }},\n"
        f"    {{\n"
        f"      \"archetype\": \"bold_prediction\",\n"
        f"      \"hook_text\": \"High conviction forecast hook text\",\n"
        f"      \"score\": 8.9,\n"
        f"      \"reasoning\": \"Why bold predictions incite comment debates\"\n"
        f"    }}\n"
        f"  ]\n"
        f"}}\n"
        f"Return ONLY valid JSON with no surrounding text."
    )

def _build_virality_system_prompt(persona: Any | None = None, goal: str = "bookmark_and_dwell") -> str:
    """Builds the viral hook & bookmark optimization system prompt."""
    display_name = _get_persona_field(persona, "display_name", default="Autonomous Creator")
    x_handle = _get_persona_field(persona, "x_handle", default="creator")
    tone = _get_persona_field(persona, "writing_style", "tone", default="sharp, authentic")
    comm_style = _get_persona_field(persona, "personality", "communication_style", default="direct, high-density")

    prompt_parts = [
        f"You are {display_name} (@{x_handle}). You are an elite viral growth engineer and copywriter for X (Twitter).",
        f"Voice Tone: {tone}. Communication Style: {comm_style}.\n",
        "=== OBJECTIVE ===",
        "Transform post drafts into high-performing X posts optimized for the Phoenix algorithm:",
        "1. OPEN-LOOP CURIOSITY HOOK (<100 CHARACTERS): The opening hook MUST be strictly under 100 characters (<100 chars) as an engaging opener.",
        "2. STRICT TOTAL LENGTH (<= 250 CHARACTERS COMBINED): The combined total length of hook + body + hashtags MUST be strictly <= 250 characters. Keep frameworks to 2-3 ultra-concise bullets so the post is NEVER cut off on standard X feeds.",
        "3. ZERO EXTERNAL LINKS: Never include external URLs in the post body (links will be routed to 1st reply).",
        "4. ZERO AI CLICHÉS: STRICTLY BANNED: 'Let's dive in', 'Buckle up', 'Game-changer', 'Delve', 'Here is why', 'In this thread', 'Mastering', 'Unpack'.",
        "5. PRESERVE SUBJECT & TOPIC ENTITIES: Do NOT strip or generalize specific names of subjects, projects, companies, or public figures. Retain the specific subject names and top trending hashtags so the post is clearly grounded in what is actually being discussed.\n",
        "=== 4 VIRAL HOOK ARCHETYPES ===",
        "- contrarian_reversal: Challenges industry dogma or common consensus with a sharp counter-intuitive truth.",
        "- asymmetric_result: Highlights an outsized return, unexpected metric, or 10x differential.",
        "- zero_to_hero: Real-world transformation from failure or ground zero to breakthrough.",
        "- framework_breakdown: Introduces a distilled blueprint, cheat sheet, or step-by-step system.",
    ]
    return "\n".join(prompt_parts)

def _build_virality_user_prompt(draft: str, goal: str = "bookmark_and_dwell") -> str:
    """Builds the user prompt for viral hook & bookmark optimization."""
    return (
        f"Goal: {goal}\n\n"
        f"Original Post Draft:\n\"\"\"\n{draft}\n\"\"\"\n\n"
        "Optimize this draft for virality, dwell retention, and bookmarks:\n"
        "1. Select the single best archetype from (contrarian_reversal, asymmetric_result, zero_to_hero, framework_breakdown).\n"
        "2. Craft an irresistible open-loop hook that is STRICTLY UNDER 100 CHARACTERS (<100 chars).\n"
        "3. Format the clean body with high-density numbered steps / bullet points / cheat sheet layout (NO external URLs).\n"
        "4. STRICT TOTAL LENGTH: The COMBINED text of hook + clean_body MUST be strictly under 250 characters total.\n"
        "5. PRESERVE SUBJECT NAMES & HASHTAGS: Do not remove specific names of subjects/topics from the draft and include relevant hashtags.\n"
        "6. Rate the bookmark-bait utility score from 1.0 to 10.0.\n\n"
        "Return a JSON object matching this schema:\n"
        "{\n"
        "  \"open_loop_hook\": \"Cliffhanger hook strictly <100 chars\",\n"
        "  \"clean_body\": \"Formatted link-free body (keep short so hook + body <= 250 chars total)\",\n"
        "  \"archetype\": \"contrarian_reversal | asymmetric_result | zero_to_hero | framework_breakdown\",\n"
        "  \"bookmark_score\": 8.5,\n"
        "  \"reasoning\": \"Why this hook and format drive dwell time and bookmarks\"\n"
        "}\n"
        "Return ONLY valid JSON."
    )

def _infer_archetype_from_text(text: str) -> str:
    """Infers the most fitting viral archetype from text heuristics."""
    text_lower = text.lower()
    if any(k in text_lower for k in ("never", "don't", "stop", "wrong", "myth", "fake", "truth", "lie", "mistake", "isn't")):
        return "contrarian_reversal"
    if any(k in text_lower for k in ("10x", "100x", "50x", "%", "$", "saved", "roi", "grew", "scale", "qps", "latency")):
        return "asymmetric_result"
    if any(k in text_lower for k in ("years ago", "started with", "from zero", "failed", "crashed", "learned", "journey", "story", "struggle")):
        return "zero_to_hero"
    return "framework_breakdown"

