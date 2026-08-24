from __future__ import annotations

import json
import logging
import re
from typing import Any, Literal
from pydantic import BaseModel, Field, field_validator

from xbot.ai.client import get_ai_client
from xbot.config import settings

logger = logging.getLogger(__name__)

VALID_ARCHETYPES = {
    "curiosity_gap",
    "contrarian",
    "framework_breakdown",
    "story_relatable",
    "statistical_data",
    "bold_prediction",
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
    "statistical_data": "statistical_data",
    "statistical-data": "statistical_data",
    "statistical": "statistical_data",
    "data": "statistical_data",
    "data_proof": "statistical_data",
    "bold_prediction": "bold_prediction",
    "bold-prediction": "bold_prediction",
    "prediction": "bold_prediction",
    "future_forecast": "bold_prediction",
}

VALID_VIRAL_ARCHETYPES = {
    "contrarian_reversal",
    "asymmetric_result",
    "zero_to_hero",
    "framework_breakdown",
}

VIRAL_ARCHETYPE_ALIASES = {
    "contrarian": "contrarian_reversal",
    "contrarian_reversal": "contrarian_reversal",
    "contrarian-reversal": "contrarian_reversal",
    "reversal": "contrarian_reversal",
    "asymmetric": "asymmetric_result",
    "asymmetric_result": "asymmetric_result",
    "asymmetric-result": "asymmetric_result",
    "asymmetry": "asymmetric_result",
    "zero_to_hero": "zero_to_hero",
    "zero-to-hero": "zero_to_hero",
    "story": "zero_to_hero",
    "transformation": "zero_to_hero",
    "framework": "framework_breakdown",
    "framework_breakdown": "framework_breakdown",
    "framework-breakdown": "framework_breakdown",
    "breakdown": "framework_breakdown",
    "curiosity_gap": "contrarian_reversal",
    "story_relatable": "zero_to_hero",
    "statistical_data": "asymmetric_result",
    "bold_prediction": "contrarian_reversal",
}

LINK_REGEX = re.compile(r'https?://[^\s)\]"]+|www\.[^\s)\]"]+', re.IGNORECASE)

BOOKMARK_KEYWORDS = {
    "framework", "cheat sheet", "cheatsheet", "swipe file", "checklist",
    "playbook", "template", "roadmap", "architecture", "breakdown",
    "actionable", "step-by-step", "blueprint", "heuristics", "mental model",
    "rules", "guide", "guide to", "tips", "mistakes", "tools", "stack",
    "lessons", "resources", "workflow", "system", "matrix", "scaling",
    "production", "tutorial", "best practices", "deep dive", "how-to", "howto"
}


def extract_links(text: str) -> tuple[str, str | None]:
    """
    Strips external links from text to avoid the -70% to -80% algorithmic reach penalty
    and isolates the primary URL for 1st-reply injection.
    """
    if not text:
        return "", None

    matches = LINK_REGEX.findall(text)
    extracted_link = matches[0].rstrip(".,;:!?") if matches else None

    # Replace markdown link syntax [text](url) -> text
    clean_text = re.sub(r'\[([^\]]+)\]\((?:https?://|www\.)[^\s)]+\)', r'\1', text)

    # Remove remaining URLs
    clean_text = LINK_REGEX.sub('', clean_text)

    # Clean up empty brackets, parens, trailing 'link:', 'url:', etc.
    clean_text = re.sub(r'\(\s*\)', '', clean_text)
    clean_text = re.sub(r'\[\s*\]', '', clean_text)
    clean_text = re.sub(r'(?:link|url|source|read more):\s*$', '', clean_text, flags=re.IGNORECASE | re.MULTILINE)

    # Clean multiple spaces on each line
    lines = []
    for line in clean_text.split('\n'):
        line_clean = re.sub(r'[ \t]+', ' ', line).strip()
        lines.append(line_clean)

    # Collapse multiple blank lines
    result = '\n'.join(lines)
    result = re.sub(r'\n{3,}', '\n\n', result).strip()
    return result, extracted_link


def calculate_bookmark_score(text: str) -> float:
    """
    Evaluates bookmark-bait utility based on numbered frameworks, action steps,
    cheat sheets, checklists, and high-density formatting (1.0 to 10.0).
    """
    if not text or not text.strip():
        return 1.0

    clean_text = text.strip()
    score = 2.5  # Base score

    # 1. Numbered items / action steps / bullets
    list_item_pattern = re.compile(
        r'^\s*(?:\d+[\.\)]|step\s*\d+[:\.]?|rule\s*\d+[:\.]?|phase\s*\d+[:\.]?|part\s*\d+[:\.]?|[•\-\*])\s+',
        re.IGNORECASE | re.MULTILINE,
    )
    list_matches = list_item_pattern.findall(clean_text)
    num_items = len(list_matches)

    if num_items >= 5:
        score += 3.5
    elif num_items >= 3:
        score += 2.5
    elif num_items >= 1:
        score += 1.5

    # 2. High-utility bookmark keywords
    text_lower = clean_text.lower()
    keyword_hits = sum(1 for kw in BOOKMARK_KEYWORDS if kw in text_lower)
    score += min(3.5, keyword_hits * 1.0)

    # 3. Multiline structure & formatting
    paragraphs = [p for p in clean_text.split('\n\n') if p.strip()]
    if len(paragraphs) >= 2 or '\n' in clean_text:
        score += 1.0

    # 4. Code snippets or monospaced text
    if '`' in clean_text:
        score += 0.5

    return max(1.0, min(10.0, round(score, 1)))


def trim_open_loop_hook(text: str, max_len: int = 99) -> str:
    """Cleans and trims hook to strictly <100 characters for mobile fold retention."""
    text = clean_hook_text(text).strip()
    if len(text) <= max_len:
        return text
    # Try to trim at punctuation boundary before max_len
    trimmed = text[:max_len]
    last_punct = max(trimmed.rfind('.'), trimmed.rfind('?'), trimmed.rfind('!'), trimmed.rfind(':'))
    if last_punct > 40:
        return trimmed[:last_punct + 1].strip()
    last_space = trimmed.rfind(' ')
    if last_space > 40:
        return trimmed[:last_space].strip()
    return trimmed.strip()


class OptimizedPostResult(BaseModel):
    open_loop_hook: str = Field(..., description="Curiosity cliffhanger strictly <100 characters before the mobile fold")
    bookmark_score: float = Field(default=5.0, ge=1.0, le=10.0, description="Bookmark-bait utility score (1.0 to 10.0)")
    clean_body: str = Field(default="", description="Link-free formatted body with numbered framework/bullet points")
    extracted_link: str | None = Field(default=None, description="Isolated external URL for 1st-reply injection")
    archetype: str = Field(
        default="framework_breakdown",
        description="Viral hook archetype: contrarian_reversal, asymmetric_result, zero_to_hero, framework_breakdown",
    )
    full_optimized_text: str = Field(default="", description="Complete formatted post combining open-loop hook and clean body")

    @field_validator("open_loop_hook")
    @classmethod
    def validate_open_loop_hook(cls, v: str) -> str:
        trimmed = v.strip()
        if len(trimmed) >= 100:
            trimmed = trim_open_loop_hook(trimmed, max_len=99)
        return trimmed

    @field_validator("bookmark_score")
    @classmethod
    def validate_bookmark_score(cls, v: float) -> float:
        return max(1.0, min(10.0, round(float(v), 2)))

    def __init__(self, **data: Any) -> None:
        arch = str(data.get("archetype", "framework_breakdown")).strip().lower()
        data["archetype"] = VIRAL_ARCHETYPE_ALIASES.get(arch, "framework_breakdown" if arch not in VALID_VIRAL_ARCHETYPES else arch)

        if "open_loop_hook" in data and isinstance(data["open_loop_hook"], str):
            hook = data["open_loop_hook"].strip()
            if len(hook) >= 100:
                data["open_loop_hook"] = trim_open_loop_hook(hook, max_len=99)

        if "full_optimized_text" not in data or not data["full_optimized_text"]:
            hook = data.get("open_loop_hook", "").strip()
            body = data.get("clean_body", "").strip()
            if hook and body:
                if body.startswith(hook):
                    data["full_optimized_text"] = body
                else:
                    data["full_optimized_text"] = f"{hook}\n\n{body}"
            elif hook:
                data["full_optimized_text"] = hook
            else:
                data["full_optimized_text"] = body
        super().__init__(**data)


class _ViralHookResponse(BaseModel):
    open_loop_hook: str = Field(..., description="Curiosity cliffhanger strictly <100 characters before the mobile fold")
    clean_body: str = Field(default="", description="Formatted body with numbered steps or frameworks, free of external links")
    archetype: Literal[
        "contrarian_reversal",
        "asymmetric_result",
        "zero_to_hero",
        "framework_breakdown",
    ] = Field(default="framework_breakdown", description="Viral hook archetype")
    bookmark_score: float = Field(default=8.0, ge=1.0, le=10.0, description="Bookmark-bait score from 1.0 to 10.0")
    reasoning: str = Field(default="", description="Why this hook creates curiosity and dwell time")


class HookCandidate(BaseModel):
    archetype: Literal[
        "curiosity_gap",
        "contrarian",
        "framework_breakdown",
        "story_relatable",
        "statistical_data",
        "bold_prediction",
    ]
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
        description="The 6 hook archetype candidates evaluated and scored",
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

        # If candidates could not be parsed from JSON, fallback safely returning original draft
        logger.warning("No valid hook candidates parsed from LLM output. Returning safe original content fallback.")
        win_cand = HookCandidate(
            archetype="curiosity_gap",
            hook_text=first_line[:140] if first_line else "Draft hook",
            score=5.0,
            reasoning="Fallback returned due to invalid JSON from LLM",
        )
        return HookOptimizationResult(
            original_content=draft_content,
            optimized_content=draft_content,
            winning_hook=win_cand,
            candidates=[win_cand],
        )

    except Exception as e:
        logger.error("Error in optimize_post_hook: %s", e)
        win_cand = HookCandidate(
            archetype="curiosity_gap",
            hook_text=first_line[:140] if first_line else "Draft hook",
            score=5.0,
            reasoning=f"Fallback returned due to API error: {e}",
        )
        return HookOptimizationResult(
            original_content=draft_content,
            optimized_content=draft_content,
            winning_hook=win_cand,
            candidates=[win_cand],
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
        "1. OPEN-LOOP CURIOSITY HOOK (<100 CHARACTERS): The opening hook MUST be strictly under 100 characters (<100 chars). It acts as an open-loop cliffhanger before the mobile 'Show more' fold to maximize dwell time (+20x Phoenix multiplier).",
        "2. BOOKMARK-BAIT FORMATTING: Format actionable value as high-density numbered steps, cheat sheets, frameworks, or swipe files to drive bookmarks (+50x multiplier).",
        "3. ZERO EXTERNAL LINKS: Never include external URLs in the post body (links will be routed to 1st reply to avoid the -70% reach penalty).",
        "4. ZERO AI CLICHÉS: STRICTLY BANNED: 'Let's dive in', 'Buckle up', 'Game-changer', 'Delve', 'Here is why', 'In this thread', 'Mastering', 'Unpack'.\n",
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
        "4. Rate the bookmark-bait utility score from 1.0 to 10.0.\n\n"
        "Return a JSON object matching this schema:\n"
        "{\n"
        "  \"open_loop_hook\": \"Cliffhanger hook strictly <100 chars\",\n"
        "  \"clean_body\": \"Formatted link-free body with numbered framework/bullet points\",\n"
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


async def optimize_post_for_virality(
    draft: str,
    goal: str = "bookmark_and_dwell",
    persona: Any | None = None,
    client: Any | None = None,
) -> OptimizedPostResult:
    """
    Optimizes a post draft for algorithmic virality:
    1. Extracts & strips external links (isolating for 1st-reply injection).
    2. Crafts an open-loop curiosity hook strictly <100 characters before the mobile fold.
    3. Formats the body as high-utility bookmark-bait (cheat sheets, checklists, numbered steps).
    4. Evaluates bookmark utility score (1.0 to 10.0).
    5. Categorizes under 4 viral archetypes (contrarian_reversal, asymmetric_result, zero_to_hero, framework_breakdown).
    """
    clean_draft, extracted_link = extract_links(draft)
    base_bookmark_score = calculate_bookmark_score(clean_draft)

    # Separate draft into first line/paragraph vs remaining body
    lines = [line.strip() for line in clean_draft.split('\n') if line.strip()]
    first_line = lines[0] if lines else "Key insights on engineering & systems."
    remaining_body = "\n\n".join(lines[1:]) if len(lines) > 1 else ""

    fallback_hook = trim_open_loop_hook(first_line, max_len=99)
    fallback_archetype = _infer_archetype_from_text(clean_draft)

    ai_client = client if client is not None else get_ai_client()
    model = getattr(
        settings,
        "MODEL_HOOK_OPTIMIZER",
        getattr(settings, "MODEL_POST_CREATION", "litellm/gpt-oss-120b"),
    )

    system_prompt = _build_virality_system_prompt(persona, goal)
    user_prompt = _build_virality_user_prompt(clean_draft, goal)

    try:
        # 1. Structured parse attempt
        try:
            completion = await ai_client.beta.chat.completions.parse(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_format=_ViralHookResponse,
            )
            parsed = getattr(completion.choices[0].message, "parsed", None)
            if parsed and isinstance(parsed, _ViralHookResponse):
                hook = trim_open_loop_hook(parsed.open_loop_hook, max_len=99)
                body_clean, body_link = extract_links(parsed.clean_body or remaining_body)
                combined_link = extracted_link or body_link
                calculated_score = calculate_bookmark_score(body_clean or clean_draft)
                score = max(calculated_score, float(parsed.bookmark_score))

                return OptimizedPostResult(
                    open_loop_hook=hook,
                    bookmark_score=min(10.0, max(1.0, score)),
                    clean_body=body_clean,
                    extracted_link=combined_link,
                    archetype=parsed.archetype,
                )
        except Exception as parse_err:
            logger.debug("Structured virality parse failed, trying standard JSON mode: %s", parse_err)

        # 2. Standard JSON mode attempt
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
            completion = await ai_client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )

        raw_content = getattr(completion.choices[0].message, "content", None)
        if isinstance(raw_content, str):
            cleaned = clean_text_for_json(raw_content)
            data = json.loads(cleaned)
            if isinstance(data, dict):
                raw_hook = str(data.get("open_loop_hook") or data.get("hook") or fallback_hook)
                hook = trim_open_loop_hook(raw_hook, max_len=99)
                raw_body = str(data.get("clean_body") or data.get("body") or remaining_body)
                body_clean, body_link = extract_links(raw_body)
                combined_link = extracted_link or body_link
                calculated_score = calculate_bookmark_score(body_clean or clean_draft)
                raw_score = float(data.get("bookmark_score", calculated_score))
                score = max(calculated_score, raw_score)
                archetype = str(data.get("archetype", fallback_archetype))

                return OptimizedPostResult(
                    open_loop_hook=hook,
                    bookmark_score=min(10.0, max(1.0, score)),
                    clean_body=body_clean,
                    extracted_link=combined_link,
                    archetype=archetype,
                )
    except Exception as e:
        logger.warning("Virality optimization model call failed: %s. Returning clean heuristic result.", e)

    # 3. Offline Heuristic Fallback
    return OptimizedPostResult(
        open_loop_hook=fallback_hook,
        bookmark_score=base_bookmark_score,
        clean_body=remaining_body,
        extracted_link=extracted_link,
        archetype=fallback_archetype,
    )
