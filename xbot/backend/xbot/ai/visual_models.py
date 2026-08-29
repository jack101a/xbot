from __future__ import annotations
from typing import Literal
from pydantic import BaseModel, Field, field_validator

class VisualPostSpec(BaseModel):
    tweet_copy: str = Field(..., description="Setup tension hook strictly under 140 characters")
    image_prompt: str = Field(..., description="Detailed visual prompt specifying 4:5 portrait aspect ratio, lighting, dark mode, high contrast")
    aspect_ratio: Literal["4:5", "1:1"] = Field(default="4:5", description="Aspect ratio (4:5 for mobile screen takeover or 1:1 square)")
    format_type: str = Field(..., description="Visual format type: storyboard_4panel, side_by_side, urban_lifestyle, dark_infographic")
    target_simcluster: str = Field(..., description="Target SimCluster: Tech/AI, Cinema/Prestige, Urban/Creator, Anime/PopCulture")
    one_two_punch_strategy: str = Field(..., description="Cognitive separation strategy where copy sets up tension and image delivers punchline")

    @field_validator("tweet_copy")
    @classmethod
    def validate_tweet_copy(cls, v: str) -> str:
        clean = " ".join(v.strip().split())
        if len(clean) >= 140:
            # Truncate cleanly at word boundary under 140 chars
            truncated = clean[:136]
            last_space = truncated.rfind(" ")
            if last_space > 80:
                clean = truncated[:last_space] + "..."
            else:
                clean = truncated + "..."
        return clean

    @field_validator("aspect_ratio")
    @classmethod
    def validate_aspect_ratio(cls, v: str) -> str:
        if v not in ("4:5", "1:1"):
            raise ValueError(f"Aspect ratio must be '4:5' or '1:1', got '{v}'")
        return v


from xbot.ai.visual_inference import infer_format_type, infer_simcluster, _build_visual_system_prompt, _build_visual_user_prompt

