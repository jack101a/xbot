from __future__ import annotations

import base64
import logging
import os
import time
import uuid
from pathlib import Path
from typing import Any, Literal

import httpx

from xbot.config import settings

logger = logging.getLogger(__name__)

# Supported NVIDIA GenAI Image Models
NVIDIA_MODELS: dict[str, str] = {
    "flux.1-dev": "black-forest-labs/flux.1-dev",
    "flux.2-klein-4b": "black-forest-labs/flux.2-klein-4b",
    "stable-diffusion-3-medium": "stabilityai/stable-diffusion-3-medium",
    "flux.1-kontext-dev": "black-forest-labs/flux.1-kontext-dev",
}

# Valid dimension snapping list for Flux models
VALID_FLUX_DIMS: list[int] = [768, 832, 896, 960, 1024, 1088, 1152, 1216, 1280, 1344]

# Preset Aspect Ratio to (width, height) mappings validated on NVIDIA GenAI
ASPECT_RATIO_PRESETS: dict[str, tuple[int, int]] = {
    "1:1": (1024, 1024),
    "4:5": (768, 960),    # Exact 4:5 aspect ratio (0.80) for X mobile feed takeover
    "16:9": (1024, 768),  # Widescreen
    "9:16": (768, 1024),  # Vertical story
    "3:2": (1024, 768),
    "2:3": (768, 1024),
}

REQUEST_TIMEOUT_SECONDS = 300


def snap_flux_dimension(dim: int) -> int:
    """Snaps an arbitrary integer dimension to the nearest valid Flux supported dimension."""
    return min(VALID_FLUX_DIMS, key=lambda x: abs(x - dim))


def extract_image_from_response(res_json: dict[str, Any]) -> str | None:
    """
    Extracts base64 encoded image from various NVIDIA response formats
    (image, artifacts[0].base64, data[0].b64_json) and checks safety filters.
    """
    if res_json.get("image"):
        return res_json["image"]

    artifacts = res_json.get("artifacts")
    if isinstance(artifacts, list) and len(artifacts) > 0:
        artifact = artifacts[0]
        if artifact.get("base64"):
            return artifact["base64"]

        reason = artifact.get("finishReason", "Unknown")
        logger.error("[NVIDIA Safety Filter Alert] Image was withheld by safety filter. Reason: %s", reason)
        return None

    data_items = res_json.get("data")
    if isinstance(data_items, list) and len(data_items) > 0:
        item = data_items[0]
        if item.get("b64_json"):
            return item["b64_json"]

    return None


def parse_kontext_example_id(value: Any) -> int | None:
    """Parses valid example IDs (0, 1, 2) for Flux Kontext models."""
    if value is None:
        return None
    try:
        x = int(str(value).strip())
        if x in {0, 1, 2}:
            return x
    except Exception:
        pass
    return None


def build_nvidia_payload(
    prompt: str,
    endpoint: str,
    negative_prompt: str = "",
    steps: int = 50,
    cfg_scale: float = 5.0,
    seed: int = 0,
    width: int = 1024,
    height: int = 1024,
    aspect_ratio: str | None = None,
    init_image: str | None = None,
    kontext_example_id: int | None = None,
) -> dict[str, Any]:
    """
    Builds the model-specific JSON payload for NVIDIA GenAI endpoints.
    """
    # Resolve dimensions from aspect ratio if provided
    if aspect_ratio and aspect_ratio in ASPECT_RATIO_PRESETS:
        width, height = ASPECT_RATIO_PRESETS[aspect_ratio]

    payload: dict[str, Any] = {"prompt": prompt, "seed": seed}

    if endpoint == "black-forest-labs/flux.1-kontext-dev":
        if kontext_example_id is not None:
            payload["image"] = f"data:image/png;example_id,{kontext_example_id}"
        elif init_image:
            init_img_str = str(init_image).strip()
            if init_img_str.startswith("data:image/png;example_id,"):
                payload["image"] = init_img_str
            else:
                maybe_id = parse_kontext_example_id(init_img_str)
                if maybe_id is not None:
                    payload["image"] = f"data:image/png;example_id,{maybe_id}"
                elif init_img_str.startswith("data:"):
                    payload["image"] = init_img_str
                else:
                    payload["image"] = f"data:image/png;base64,{init_img_str}"
        else:
            raise ValueError(
                "Kontext model requires an image. Provide either init_image (base64/data URL) or kontext_example_id (0,1,2)."
            )

        payload["aspect_ratio"] = "match_input_image"
        payload["steps"] = min(steps, 30)
        payload["cfg_scale"] = cfg_scale

    elif endpoint == "black-forest-labs/flux.2-klein-4b":
        max_klein_dim = 1024
        payload["width"] = snap_flux_dimension(min(width, max_klein_dim))
        payload["height"] = snap_flux_dimension(min(height, max_klein_dim))
        payload["steps"] = 4
        # Klein prompt length cap
        if len(prompt) > 800:
            logger.info("[NVIDIA Klein] Truncating prompt from %d to 800 characters.", len(prompt))
            payload["prompt"] = prompt[:800]

    elif endpoint == "black-forest-labs/flux.1-dev":
        payload["mode"] = "base"
        payload["steps"] = min(steps, 50)
        payload["cfg_scale"] = cfg_scale
        payload["width"] = snap_flux_dimension(width)
        payload["height"] = snap_flux_dimension(height)

    else:
        # Stable Diffusion 3 / Standard aspect_ratio endpoint
        if aspect_ratio in ("1:1", "16:9", "9:16"):
            payload["aspect_ratio"] = aspect_ratio
        elif width == height:
            payload["aspect_ratio"] = "1:1"
        elif width > height:
            payload["aspect_ratio"] = "16:9"
        else:
            payload["aspect_ratio"] = "9:16"

        payload["cfg_scale"] = cfg_scale
        payload["steps"] = steps
        if negative_prompt:
            payload["negative_prompt"] = negative_prompt

    return payload


async def generate_nvidia_image_async(
    prompt: str,
    model_name: str | None = None,
    negative_prompt: str = "",
    steps: int = 50,
    cfg_scale: float = 5.0,
    seed: int = 0,
    width: int = 1024,
    height: int = 1024,
    aspect_ratio: str | None = None,
    init_image: str | None = None,
    kontext_example_id: int | None = None,
    api_key: str | None = None,
    base_url: str | None = None,
) -> str:
    """
    Asynchronously calls the NVIDIA GenAI API to generate an image from prompt.
    Returns the raw base64 string of the generated PNG image.
    """
    resolved_api_key = api_key or getattr(settings, "NVIDIA_API_KEY", None) or os.getenv("NVIDIA_API_KEY")
    if not resolved_api_key or resolved_api_key.startswith("PASTE_YOUR"):
        raise ValueError("NVIDIA API Key is missing. Set NVIDIA_API_KEY in environment or .env file.")

    resolved_base_url = (base_url or getattr(settings, "NVIDIA_BASE_URL", None) or "https://ai.api.nvidia.com/v1/genai").rstrip("/")
    chosen_model = model_name or getattr(settings, "NVIDIA_DEFAULT_IMAGE_MODEL", "flux.1-dev") or "flux.1-dev"

    # Candidate cascade order (flux.1-dev preferred)
    cascade = [chosen_model]
    for alt in ["flux.1-dev", "flux.2-klein-4b"]:
        if alt not in cascade:
            cascade.append(alt)

    headers = {
        "Authorization": f"Bearer {resolved_api_key}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }

    last_err: Exception | None = None
    for target_model in cascade:
        endpoint = NVIDIA_MODELS.get(target_model, NVIDIA_MODELS.get("flux.2-klein-4b", "black-forest-labs/flux.2-klein-4b"))
        url = f"{resolved_base_url}/{endpoint}"

        payload = build_nvidia_payload(
            prompt=prompt,
            endpoint=endpoint,
            negative_prompt=negative_prompt,
            steps=steps,
            cfg_scale=cfg_scale,
            seed=seed,
            width=width,
            height=height,
            aspect_ratio=aspect_ratio,
            init_image=init_image,
            kontext_example_id=kontext_example_id,
        )

        logger.info("Sending request to NVIDIA GenAI model '%s' (prompt: %.50s...)", target_model, prompt)

        try:
            async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT_SECONDS) as client:
                response = await client.post(url, headers=headers, json=payload)
                if response.status_code == 200:
                    res_json = response.json()
                    b64 = extract_image_from_response(res_json)
                    if b64:
                        if isinstance(b64, str) and b64.startswith("data:"):
                            b64 = b64.split(",", 1)[1]
                        return b64
                    logger.warning("NVIDIA model '%s' returned HTTP 200 without image. Trying fallback...", target_model)
                else:
                    logger.warning("NVIDIA model '%s' returned HTTP %s: %s. Trying fallback...", target_model, response.status_code, response.text[:120])
                    last_err = RuntimeError(f"NVIDIA API error ({response.status_code}): {response.text}")
        except Exception as exc:
            logger.warning("NVIDIA model '%s' request failed: %s. Trying fallback...", target_model, exc)
            last_err = exc

    raise last_err or RuntimeError("All NVIDIA image generation models in cascade failed.")


async def generate_and_save_nvidia_image_async(
    prompt: str,
    output_dir: str | Path | None = None,
    filename: str | None = None,
    model_name: str | None = None,
    negative_prompt: str = "",
    steps: int = 50,
    cfg_scale: float = 5.0,
    seed: int = 0,
    width: int = 1024,
    height: int = 1024,
    aspect_ratio: str | None = "4:5",
    init_image: str | None = None,
    kontext_example_id: int | None = None,
    api_key: str | None = None,
) -> str:
    """
    Generates an image via NVIDIA API and saves it directly to disk as a PNG file.
    Returns the absolute path to the saved image file.
    """
    b64_image = await generate_nvidia_image_async(
        prompt=prompt,
        model_name=model_name,
        negative_prompt=negative_prompt,
        steps=steps,
        cfg_scale=cfg_scale,
        seed=seed,
        width=width,
        height=height,
        aspect_ratio=aspect_ratio,
        init_image=init_image,
        kontext_example_id=kontext_example_id,
        api_key=api_key,
    )

    # Resolve output directory
    target_dir = Path(output_dir) if output_dir else Path("/home/ubuntu/projects/xbot/data/media")
    target_dir.mkdir(parents=True, exist_ok=True)

    if not filename:
        resolved_tag = str(model_name or getattr(settings, "NVIDIA_DEFAULT_IMAGE_MODEL", "flux.1-dev") or "flux.1-dev").replace("/", "_")
        filename = f"nvidia_{resolved_tag}_{int(time.time())}_{uuid.uuid4().hex[:6]}.png"
    elif not filename.endswith(".png"):
        filename = f"{filename}.png"

    file_path = target_dir / filename
    image_bytes = base64.b64decode(b64_image)
    try:
        import io
        from PIL import Image
        im = Image.open(io.BytesIO(image_bytes))
        im.save(file_path, format="PNG")
    except Exception:
        file_path.write_bytes(image_bytes)

    logger.info("Successfully saved generated NVIDIA image (%d bytes) to: %s", os.path.getsize(file_path), file_path)
    return str(file_path.resolve())
