from __future__ import annotations

import json
import logging
import re
from typing import Any, Literal
from pydantic import BaseModel, Field

from xbot.ai.client import get_ai_client
from xbot.config import settings

logger = logging.getLogger(__name__)

VALID_ARCHETYPES = {
    "curiosity_gap",
    "contrarian",
    "framework_breakdown",
    "story_relatable",
}

ARCHETYPE_ALIASES = {
    "curiosity_gap": "curiosity_gap",
    "curiosity-gap": "curiosity_gap",
    "curiosity": "curiosity_gap",
    "contrarian": "contrarian",
    "contrarian_take": "contrarian",
    "framework_breakdown": "framework_breakdown",
    "framework-breakdown": "framework_breakdown",
    "framework": "framework_breakdown",
    "story_relatable": "story_relatable",
    "story-relatable": "story_relatable",
    "story": "story_relatable",
    "relatable": "story_relatable",
}


class HookCandidate(BaseModel):
    archetype: Literal["curiosity_gap", "contrarian", "framework_breakdown", "story_relatable"]
    hook_text: str = Field(..., description="Opening hook text (<140 chars)")
    score: float = Field(default=5.0, ge=1.0, le=10.0, description="Dwell retention score")
    reasoning: str = Field(default="", description="Evaluation reasoning")


class HookOptimizationResult(BaseModel):
    original_content: str
    optimized_content: str
    winning_hook: HookCandidate
    candidates: list[HookCandidate] = Field(default_factory=list)


class _HookGenerationResponse(BaseModel):
    candidates: list[HookCandidate] = Field(
        default_factory=list,
        description="The 4 hook archetype candidates evaluated and scored",
    )


def clean_text_for_json(text: str) -> str:
    """Clean markdown code fences from LLM output."""
    text = text.strip()
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()


def clean_hook_text(text: str) -> str:
    """Cleans hook text of quotes and archetype prefixes."""
    text = text.strip()
    # Remove archetype / label prefixes like "Contrarian: ", "Hook 1: ", etc.
    text = re.sub(
        r"^(?:curiosity[_\s-]?gap|contrarian|framework[_\s-]?breakdown|story[_\s-]?relatable|hook\s*\d*|opening|option\s*\d*):\s*",
        "",
        text,
        flags=re.IGNORECASE,
    )
    text = text.strip().strip('"\'`')
    if len(text) > 140:
        text = text[:140].strip()
    return text


def format_optimized_post(draft_content: str, winning_hook_text: str) -> str:
    """
    Formats the post by substituting the draft's opening line with the winning hook
    and applying micro-spacing to maximize dwell time on the X feed.
    """
    draft = draft_content.strip()
    hook = winning_hook_text.strip()
    if not draft:
        return hook

    # Case 1: Multiple paragraphs separated by double newlines
    paragraphs = [p.strip() for p in draft.split("\n\n") if p.strip()]
    if len(paragraphs) > 1:
        body = "\n\n".join(paragraphs[1:])
        return f"{hook}\n\n{body}"

    # Case 2: Multiple lines separated by single newlines
    lines = [l.strip() for l in draft.split("\n") if l.strip()]
    if len(lines) > 1:
        body = "\n\n".join(lines[1:])
        return f"{hook}\n\n{body}"

    # Case 3: Single paragraph with multiple sentences
    sentences = re.split(r"(?<=[.!?])\s+", draft)
    if len(sentences) > 1:
        body = "\n\n".join(sentences[1:])
        return f"{hook}\n\n{body}"

    return hook


def _get_persona_field(obj: Any, *keys: str, default: Any = None) -> Any:
    """Safely extracts nested field from persona object or dict."""
    current = obj
    for key in keys:
        if current is None:
            return default
        if isinstance(current, dict):
            current = current.get(key)
        else:
            current = getattr(current, key, None)
    return current if current is not None else default


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
        "\n=== 4 VIRAL HOOK ARCHETYPES (REQUIRED) ===\n"
        "1. curiosity_gap: Creates an irresistible information gap or provocative mystery that forces the reader to stop scrolling.\n"
        "2. contrarian: Directly challenges conventional wisdom, industry dogma, or common consensus with a sharp counter-intuitive claim.\n"
        "3. framework_breakdown: Promises a distilled, actionable mental model, taxonomy, or high-density tactical teardown.\n"
        "4. story_relatable: Opens with an immediate, gritty, first-person narrative hook or battle-tested real-world scenario."
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
        f"Generate exactly 4 hook candidates (one for each archetype: curiosity_gap, contrarian, framework_breakdown, story_relatable).\n"
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
        f"    }}\n"
        f"  ]\n"
        f"}}\n"
        f"Return ONLY valid JSON with no surrounding text."
    )


def _normalize_candidate(raw: dict[str, Any], default_archetype: str = "curiosity_gap") -> HookCandidate | None:
    """Normalizes a raw candidate dict into a validated HookCandidate."""
    if not isinstance(raw, dict):
        return None

    raw_archetype = str(raw.get("archetype") or default_archetype).strip().lower()
    archetype = ARCHETYPE_ALIASES.get(raw_archetype, default_archetype)
    if archetype not in VALID_ARCHETYPES:
        archetype = "curiosity_gap"

    hook_text = clean_hook_text(str(raw.get("hook_text") or raw.get("hook") or raw.get("text") or ""))
    if not hook_text:
        return None

    try:
        score = float(raw.get("score", 5.0))
        score = max(1.0, min(10.0, score))
    except (ValueError, TypeError):
        score = 5.0

    reasoning = str(raw.get("reasoning") or raw.get("explanation") or "").strip()

    return HookCandidate(
        archetype=archetype,  # type: ignore[arg-type]
        hook_text=hook_text,
        score=score,
        reasoning=reasoning,
    )


def _parse_candidates_from_json(raw_content: Any) -> list[HookCandidate]:
    """Extracts HookCandidate list from various JSON structures."""
    if not raw_content or not isinstance(raw_content, str):
        return []

    try:
        cleaned = clean_text_for_json(raw_content)
        data = json.loads(cleaned)
    except Exception as e:
        logger.warning("Failed to decode JSON from hook optimizer response: %s", e)
        return []

    candidates: list[HookCandidate] = []

    if isinstance(data, dict):
        # Case 1: {"candidates": [...]}
        if "candidates" in data and isinstance(data["candidates"], list):
            for item in data["candidates"]:
                cand = _normalize_candidate(item)
                if cand:
                    candidates.append(cand)
        # Case 2: {"hooks": [...]}
        elif "hooks" in data and isinstance(data["hooks"], list):
            for item in data["hooks"]:
                cand = _normalize_candidate(item)
                if cand:
                    candidates.append(cand)
        # Case 3: Keyed by archetype {"curiosity_gap": {...}, "contrarian": {...}}
        else:
            for arch_key, item in data.items():
                if isinstance(item, dict):
                    cand = _normalize_candidate(item, default_archetype=arch_key)
                    if cand:
                        candidates.append(cand)

    elif isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                cand = _normalize_candidate(item)
                if cand:
                    candidates.append(cand)

    return candidates


async def optimize_post_hook(
    persona: Any,
    draft_content: str,
    topic: str = "",
    client: Any | None = None,
) -> HookOptimizationResult:
    """
    Optimizes a post draft by generating and evaluating 4 hook archetypes:
    - curiosity_gap
    - contrarian
    - framework_breakdown
    - story_relatable

    Scores each on dwell retention and scroll-stopping power, selects the winning hook,
    and formats the final post with micro-spacing. Falls back safely to original content on errors.
    """
    system_prompt = _build_hook_optimizer_system_prompt(persona, topic)
    user_prompt = _build_hook_optimizer_user_prompt(draft_content, topic)

    model = getattr(
        settings,
        "MODEL_HOOK_OPTIMIZER",
        getattr(settings, "MODEL_POST_CREATION", "litellm/gpt-oss-120b"),
    )

    ai_client = client if client is not None else get_ai_client()

    first_line = draft_content.strip().split("\n")[0].strip() if draft_content.strip() else "Draft hook"
    fallback_hook = HookCandidate(
        archetype="curiosity_gap",
        hook_text=first_line[:140] if first_line else "Draft hook",
        score=5.0,
        reasoning="Default fallback hook",
    )

    try:
        # 1. Attempt structured parse via beta endpoint
        try:
            completion = await ai_client.beta.chat.completions.parse(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_format=_HookGenerationResponse,
            )
            parsed = getattr(completion.choices[0].message, "parsed", None)
            parsed_candidates = getattr(parsed, "candidates", None) if parsed is not None else None

            if parsed_candidates and isinstance(parsed_candidates, (list, tuple)):
                sanitized_candidates: list[HookCandidate] = []
                for cand in parsed_candidates:
                    if isinstance(cand, HookCandidate):
                        sanitized_candidates.append(
                            HookCandidate(
                                archetype=cand.archetype,
                                hook_text=clean_hook_text(cand.hook_text),
                                score=max(1.0, min(10.0, float(cand.score))),
                                reasoning=cand.reasoning,
                            )
                        )
                    elif isinstance(cand, dict):
                        norm = _normalize_candidate(cand)
                        if norm:
                            sanitized_candidates.append(norm)

                if sanitized_candidates:
                    winning_hook = max(sanitized_candidates, key=lambda c: c.score)
                    optimized_content = format_optimized_post(draft_content, winning_hook.hook_text)
                    return HookOptimizationResult(
                        original_content=draft_content,
                        optimized_content=optimized_content,
                        winning_hook=winning_hook,
                        candidates=sanitized_candidates,
                    )
        except Exception as parse_err:
            logger.warning("Structured parse failed for hook optimizer, falling back: %s", parse_err)

        # 2. Fallback to standard chat completions with JSON mode
        try:
            completion = await ai_client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
            )
        except Exception:
            # Fallback without json_object mode
            completion = await ai_client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )

        raw_content = getattr(completion.choices[0].message, "content", None)
        if isinstance(raw_content, str):
            candidates = _parse_candidates_from_json(raw_content)
        else:
            candidates = []

        if candidates:
            winning_hook = max(candidates, key=lambda c: c.score)
            optimized_content = format_optimized_post(draft_content, winning_hook.hook_text)
            return HookOptimizationResult(
                original_content=draft_content,
                optimized_content=optimized_content,
                winning_hook=winning_hook,
                candidates=candidates,
            )

        # If candidates could not be parsed from JSON, fallback safely
        logger.warning("No valid hook candidates parsed from LLM output. Returning original content.")
        return HookOptimizationResult(
            original_content=draft_content,
            optimized_content=draft_content,
            winning_hook=fallback_hook,
            candidates=[fallback_hook],
        )

    except Exception as e:
        logger.error("Error in optimize_post_hook: %s", e)
        error_fallback_hook = HookCandidate(
            archetype="curiosity_gap",
            hook_text=first_line[:140] if first_line else "Draft hook",
            score=5.0,
            reasoning=f"Fallback due to error: {e}",
        )
        return HookOptimizationResult(
            original_content=draft_content,
            optimized_content=draft_content,
            winning_hook=error_fallback_hook,
            candidates=[error_fallback_hook],
        )
