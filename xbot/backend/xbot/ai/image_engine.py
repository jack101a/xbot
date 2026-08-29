"""
Unified AI Image Generation Engine for XBot Pro.

Routes visual prompts through a prioritized provider cascade:
1. Primary: ChatGPT Web Bridge (DALL-E 3 / GPT-4o for studio-grade realism & typography)
2. Fallback: NVIDIA GenAI API (Flux.1-dev / Flux.2-klein-4b)
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Literal

from xbot.ai.chatgpt_image import generate_and_save_chatgpt_image_async
from xbot.ai.nvidia_image import generate_and_save_nvidia_image_async
from xbot.config import settings

logger = logging.getLogger(__name__)


async def generate_post_image_async(
    prompt: str,
    output_dir: str | Path | None = None,
    filename: str | None = None,
    aspect_ratio: str = "4:5",
    provider_preference: Literal["auto", "chatgpt", "nvidia"] = "auto",
) -> str:
    """
    Generates and saves a post/thread image using the configured image generation provider cascade.
    
    Returns the absolute path to the saved image.
    """
    configured_cascade = getattr(settings, "IMAGE_GENERATION_PROVIDER", "chatgpt,nvidia")
    providers = [p.strip().lower() for p in configured_cascade.split(",") if p.strip()]

    if provider_preference in ("chatgpt", "nvidia"):
        # Explicit override
        providers = [provider_preference] + [p for p in providers if p != provider_preference]

    last_error: Exception | None = None

    for provider in providers:
        if provider == "chatgpt":
            if not getattr(settings, "CHATGPT_BRIDGE_ENABLED", True):
                continue
            try:
                logger.info("Attempting image generation via ChatGPT Bridge...")
                return await generate_and_save_chatgpt_image_async(
                    prompt=prompt,
                    output_dir=output_dir,
                    filename=filename,
                    aspect_ratio=aspect_ratio,
                )
            except Exception as exc:
                logger.warning("ChatGPT Bridge image generation failed (%s). Trying next provider...", exc)
                last_error = exc

        elif provider == "nvidia":
            try:
                logger.info("Attempting image generation via NVIDIA GenAI...")
                return await generate_and_save_nvidia_image_async(
                    prompt=prompt,
                    output_dir=output_dir,
                    filename=filename,
                    aspect_ratio=aspect_ratio,
                )
            except Exception as exc:
                logger.warning("NVIDIA GenAI image generation failed (%s).", exc)
                last_error = exc

    raise last_error or RuntimeError("All image generation providers in cascade failed.")
