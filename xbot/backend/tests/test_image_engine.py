import pytest
from unittest.mock import AsyncMock, patch
from pathlib import Path

from xbot.ai.image_engine import generate_post_image_async


@pytest.mark.asyncio
async def test_generate_post_image_chatgpt_primary(tmp_path: Path):
    mock_out = tmp_path / "chatgpt_test.png"
    mock_out.write_bytes(b"PNG_MOCK_DATA")

    with patch("xbot.ai.image_engine.generate_and_save_chatgpt_image_async", new_callable=AsyncMock) as mock_chatgpt:
        mock_chatgpt.return_value = str(mock_out)

        img_path = await generate_post_image_async(
            prompt="A futuristic neon city",
            aspect_ratio="4:5",
            provider_preference="chatgpt",
        )

        assert img_path == str(mock_out)
        assert mock_chatgpt.called


@pytest.mark.asyncio
async def test_generate_post_image_cascade_to_nvidia(tmp_path: Path):
    mock_nvidia_out = tmp_path / "nvidia_fallback.png"
    mock_nvidia_out.write_bytes(b"NVIDIA_MOCK_DATA")

    with patch("xbot.ai.image_engine.generate_and_save_chatgpt_image_async", new_callable=AsyncMock) as mock_chatgpt, \
         patch("xbot.ai.image_engine.generate_and_save_nvidia_image_async", new_callable=AsyncMock) as mock_nvidia:

        mock_chatgpt.side_effect = RuntimeError("Session expired")
        mock_nvidia.return_value = str(mock_nvidia_out)

        img_path = await generate_post_image_async(
            prompt="A 3D golden checkmark",
            aspect_ratio="4:5",
            provider_preference="auto",
        )

        assert img_path == str(mock_nvidia_out)
        assert mock_chatgpt.called
        assert mock_nvidia.called
