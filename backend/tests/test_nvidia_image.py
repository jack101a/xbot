import base64
import json
import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from xbot.ai.nvidia_image import (
    NVIDIA_MODELS,
    VALID_FLUX_DIMS,
    build_nvidia_payload,
    extract_image_from_response,
    generate_and_save_nvidia_image_async,
    generate_nvidia_image_async,
    parse_kontext_example_id,
    snap_flux_dimension,
)


def test_snap_flux_dimension():
    """Verifies that dimensions snap to the nearest valid Flux dimension."""
    assert snap_flux_dimension(1000) == 1024
    assert snap_flux_dimension(700) == 768
    assert snap_flux_dimension(1400) == 1344
    assert snap_flux_dimension(830) == 832
    assert snap_flux_dimension(1024) == 1024


def test_parse_kontext_example_id():
    """Verifies parsing of valid example IDs."""
    assert parse_kontext_example_id(0) == 0
    assert parse_kontext_example_id("1") == 1
    assert parse_kontext_example_id(2) == 2
    assert parse_kontext_example_id(3) is None
    assert parse_kontext_example_id("invalid") is None
    assert parse_kontext_example_id(None) is None


def test_build_nvidia_payload_flux_dev():
    """Verifies payload construction for flux.1-dev."""
    payload = build_nvidia_payload(
        prompt="A cinematic Cyberpunk city",
        endpoint="black-forest-labs/flux.1-dev",
        steps=30,
        cfg_scale=4.5,
        seed=42,
        width=1000,
        height=1300,
    )
    assert payload["prompt"] == "A cinematic Cyberpunk city"
    assert payload["seed"] == 42
    assert payload["mode"] == "base"
    assert payload["width"] == 1024  # snapped from 1000
    assert payload["height"] == 1280  # snapped from 1300
    assert payload["steps"] == 30
    assert payload["cfg_scale"] == 4.5


def test_build_nvidia_payload_flux_klein():
    """Verifies payload construction and prompt truncation for flux.2-klein-4b."""
    long_prompt = "a" * 1000
    payload = build_nvidia_payload(
        prompt=long_prompt,
        endpoint="black-forest-labs/flux.2-klein-4b",
        width=1200,
        height=1200,
    )
    assert len(payload["prompt"]) == 800
    assert payload["steps"] == 4
    assert payload["width"] == 1024  # capped at 1024
    assert payload["height"] == 1024


def test_build_nvidia_payload_sd3():
    """Verifies payload construction for stable-diffusion-3-medium."""
    payload = build_nvidia_payload(
        prompt="Studio portrait",
        endpoint="stabilityai/stable-diffusion-3-medium",
        negative_prompt="blurry, distorted",
        aspect_ratio="16:9",
        steps=25,
    )
    assert payload["prompt"] == "Studio portrait"
    assert payload["negative_prompt"] == "blurry, distorted"
    assert payload["aspect_ratio"] == "16:9"
    assert payload["steps"] == 25


def test_build_nvidia_payload_kontext():
    """Verifies payload construction for flux.1-kontext-dev."""
    payload = build_nvidia_payload(
        prompt="Add sunglasses",
        endpoint="black-forest-labs/flux.1-kontext-dev",
        kontext_example_id=1,
    )
    assert payload["image"] == "data:image/png;example_id,1"
    assert payload["aspect_ratio"] == "match_input_image"

    with pytest.raises(ValueError):
        build_nvidia_payload(
            prompt="Missing image",
            endpoint="black-forest-labs/flux.1-kontext-dev",
        )


def test_extract_image_from_response():
    """Verifies extraction across multiple NVIDIA API response formats."""
    # 1. Direct image field
    assert extract_image_from_response({"image": "b64_raw_data"}) == "b64_raw_data"

    # 2. Artifacts list
    assert extract_image_from_response({"artifacts": [{"base64": "b64_artifact_data"}]}) == "b64_artifact_data"

    # 3. Data list (OpenAI-compatible)
    assert extract_image_from_response({"data": [{"b64_json": "b64_data_json"}]}) == "b64_data_json"

    # 4. Safety filter triggered
    assert extract_image_from_response({"artifacts": [{"finishReason": "CONTENT_FILTERED"}]}) is None
    assert extract_image_from_response({}) is None


@pytest.mark.asyncio
async def test_generate_nvidia_image_async():
    """Verifies successful asynchronous API call to NVIDIA GenAI."""
    mock_b64 = base64.b64encode(b"fake_png_image_bytes").decode("utf-8")
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"image": mock_b64}

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response

        res = await generate_nvidia_image_async(
            prompt="A futuristic spaceship",
            model_name="flux.1-dev",
            api_key="nvapi-testkey123",
        )

        assert res == mock_b64
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert "ai.api.nvidia.com" in call_args[0][0]
        assert call_args[1]["headers"]["Authorization"] == "Bearer nvapi-testkey123"


@pytest.mark.asyncio
async def test_generate_and_save_nvidia_image_async(tmp_path):
    """Verifies generating and saving image directly to disk."""
    fake_bytes = b"fake_png_binary_content"
    mock_b64 = base64.b64encode(fake_bytes).decode("utf-8")

    with patch("xbot.ai.nvidia_image.generate_nvidia_image_async", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = mock_b64

        saved_path = await generate_and_save_nvidia_image_async(
            prompt="A high-contrast infographic",
            output_dir=tmp_path,
            filename="test_output.png",
            api_key="nvapi-testkey123",
        )

        assert os.path.exists(saved_path)
        assert Path(saved_path).read_bytes() == fake_bytes
