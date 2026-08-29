from __future__ import annotations
from typing import Any, Literal
from pydantic import BaseModel, Field, field_validator
from xbot.ai.anti_ai_gatekeeper import strip_surrounding_quotes
from .constants import VALID_VIRAL_ARCHETYPES, VIRAL_ARCHETYPE_ALIASES

def _trim_hook_str(text: str, max_len: int = 99) -> str:
    if len(text) <= max_len:
        return text
    truncated = text[:max_len]
    last_space = truncated.rfind(" ")
    if last_space > 20:
        return truncated[:last_space].rstrip(".,;:-—")
    return truncated.rstrip(".,;:-—")

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
            trimmed = _trim_hook_str(trimmed, max_len=99)
        return trimmed

    @field_validator("bookmark_score")
    @classmethod
    def validate_bookmark_score(cls, v: float) -> float:
        return max(1.0, min(10.0, round(float(v), 2)))

    def __init__(self, **data: Any) -> None:
        arch = str(data.get("archetype", "framework_breakdown")).strip().lower()
        data["archetype"] = VIRAL_ARCHETYPE_ALIASES.get(arch, "framework_breakdown" if arch not in VALID_VIRAL_ARCHETYPES else arch)

        if "open_loop_hook" in data and isinstance(data["open_loop_hook"], str):
            hook = strip_surrounding_quotes(data["open_loop_hook"].strip())
            if len(hook) >= 100:
                hook = _trim_hook_str(hook, max_len=99)
            data["open_loop_hook"] = hook

        if "clean_body" in data and isinstance(data["clean_body"], str):
            data["clean_body"] = strip_surrounding_quotes(data["clean_body"].strip())

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

        if "full_optimized_text" in data and isinstance(data["full_optimized_text"], str):
            data["full_optimized_text"] = strip_surrounding_quotes(data["full_optimized_text"].strip())

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
