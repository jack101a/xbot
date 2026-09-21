"""
Studio-Grade Image Generation via ChatGPT Web Bridge (DALL-E 3 / GPT-4o).

Submits detailed visual prompts to the standalone ChatGPT Bridge container,
waits for high-res generation, and saves the resulting PNG directly to disk.
Works across localhost, LAN, or remote VPS deployment with zero in-process browser overhead.
"""

from __future__ import annotations

import asyncio
import logging
import os
import shutil
import time
import uuid
from pathlib import Path

import httpx

from xbot.ai.chatgpt_adapter import get_bridge_url
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
    target_dir = Path(output_dir) if output_dir else (Path(settings.BASE_PROFILE_DIR).parent / "media")
    target_dir.mkdir(parents=True, exist_ok=True)

    # Format visual prompt with explicit framing instructions
    ratio_directive = "4:5 portrait aspect ratio" if aspect_ratio == "4:5" else f"{aspect_ratio} aspect ratio"
    enhanced_prompt = (
        f"Generate a high-quality, professional image in {ratio_directive}: {prompt}. "
        "High resolution, clean crisp modern details, zero realistic humans, no human faces."
    )

    bridge_url = get_bridge_url()
    logger.info("Requesting image from ChatGPT Web Bridge at %s (aspect: %s, prompt: %.60s...)", bridge_url, aspect_ratio, prompt)

    payload = {
        "prompt": enhanced_prompt,
        "timeout_s": timeout_s,
        "max_tries": 5,
        "client_id": "xbot",
    }

    try:
        async with httpx.AsyncClient(timeout=float(timeout_s + 30)) as client:
            resp = await client.post(f"{bridge_url}/image", json=payload)
            if resp.status_code != 200:
                raise RuntimeError(f"ChatGPT bridge returned HTTP {resp.status_code}: {resp.text[:300]}")

            res = resp.json()
            if "error" in res:
                raise RuntimeError(f"ChatGPT bridge image generation error: {res.get('error')}")

            # Extract target filename
            out_name = filename if filename else f"{uuid.uuid4().hex[:12]}.png"
            if not out_name.endswith(".png"):
                out_name = f"{out_name}.png"
            target_file = target_dir / out_name

            # Preferred: download via image_url
            image_url = res.get("image_url")
            raw_path_str = res.get("path")

            if image_url:
                download_url = f"{bridge_url}{image_url}" if image_url.startswith("/") else image_url
                img_resp = await client.get(download_url)
                if img_resp.status_code == 200 and len(img_resp.content) > 1000:
                    target_file.write_bytes(img_resp.content)
                    logger.info("Successfully downloaded and saved ChatGPT image to: %s (%d bytes)", target_file, len(img_resp.content))
                    return str(target_file.resolve())

            # Fallback: check if local path exists (e.g. shared volume)
            if raw_path_str and Path(raw_path_str).exists():
                saved_path = Path(raw_path_str)
                if saved_path.resolve() != target_file.resolve():
                    shutil.copy2(str(saved_path), str(target_file))
                logger.info("Successfully copied ChatGPT image from local path to: %s", target_file)
                return str(target_file.resolve())

            raise RuntimeError(f"ChatGPT bridge returned no downloadable image: {res}")

    except httpx.ConnectError as ce:
        logger.warning("ChatGPT bridge offline at %s: %s", bridge_url, ce)
        raise RuntimeError(f"ChatGPT bridge offline at {bridge_url}") from ce
    except Exception as exc:
        logger.warning("ChatGPT image generation error: %s", exc)
        raise RuntimeError(f"ChatGPT image generation failed: {exc}") from exc
