"""
Studio-Grade Image Generation via ChatGPT Web Bridge (DALL-E 3 / GPT-4o).

Submits detailed visual prompts to the ChatGPT web composer,
waits for high-res generation, and saves the resulting PNG directly to disk.
"""

from __future__ import annotations

import asyncio
import logging
import os
import shutil
import time
import uuid
from pathlib import Path

from xbot.ai.chatgpt_adapter import get_chatgpt_instance, _bridge_lock
from xbot.ai.chatgpt_bridge.errors import (
    AuthError,
    BridgeTimeoutError,
    ShapeChangedError,
)
from xbot.config import settings

logger = logging.getLogger(__name__)


async def generate_and_save_chatgpt_image_async(
    prompt: str,
    output_dir: str | Path | None = None,
    filename: str | None = None,
    aspect_ratio: str = "1:1",
    timeout_s: int = 300,
) -> str:
    """
    Generates a studio-grade image via ChatGPT web bridge and saves it to disk.
    
    Returns the absolute path to the saved PNG image.
    """
    target_dir = Path(output_dir) if output_dir else Path("/home/ubuntu/projects/xbot/data/media")
    target_dir.mkdir(parents=True, exist_ok=True)

    # Format visual prompt with explicit framing instructions
    ratio_directive = "4:5 portrait aspect ratio" if aspect_ratio == "4:5" else f"{aspect_ratio} aspect ratio"
    enhanced_prompt = (
        f"Generate a high-quality, professional image in {ratio_directive}: {prompt}. "
        "High resolution, cinematic lighting, ultra-clean details."
    )

    logger.info("Requesting image from ChatGPT Web Bridge (aspect: %s, prompt: %.60s...)", aspect_ratio, prompt)

    async with _bridge_lock:
        bridge = get_chatgpt_instance()
        try:
            res = await bridge.generate_image(
                prompt=enhanced_prompt,
                timeout_s=timeout_s,
            )
            raw_path_str = res.get("path")
            if not raw_path_str or not Path(raw_path_str).exists():
                raise RuntimeError(f"ChatGPT did not return a valid saved image path: {res}")

            saved_path = Path(raw_path_str)

            # Move/rename to target output_dir
            target_file = target_dir / (filename if filename else saved_path.name)
            if not target_file.name.endswith(".png"):
                target_file = target_file.with_suffix(".png")
            if saved_path.resolve() != target_file.resolve():
                shutil.move(str(saved_path), str(target_file))
                saved_path = target_file

            logger.info("Successfully generated and saved ChatGPT image to: %s", saved_path)
            return str(saved_path.resolve())

        except (AuthError, ShapeChangedError, BridgeTimeoutError) as exc:
            logger.warning("ChatGPT image generation error: %s", exc)
            raise RuntimeError(f"ChatGPT image generation failed: {exc}") from exc
