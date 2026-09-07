"""
xbot.infra.llm.adapter: Concrete implementation of LLMPort wrapping RoutingClient and ImageEngine.
"""
from __future__ import annotations

import logging
from typing import Any

from xbot.ai.client import RoutingClient
from xbot.ai.nvidia_image import generate_nvidia_image_async, generate_and_save_nvidia_image_async
from xbot.contracts.ports import LLMPort

logger = logging.getLogger(__name__)


class UnifiedLLMAdapter(LLMPort):
    """Unified LLM adapter implementing LLMPort across all AI models (LiteLLM, ChatGPT, DeepSeek, Gemini)."""

    def __init__(self, client: RoutingClient | None = None) -> None:
        self._client = client or RoutingClient()

    async def complete(
        self,
        prompt: str,
        *,
        model: str | None = None,
        temperature: float = 0.7,
        response_schema: dict[str, Any] | None = None,
    ) -> str:
        messages = [{"role": "user", "content": prompt}]
        kwargs: dict[str, Any] = {
            "messages": messages,
            "temperature": temperature,
        }
        if model:
            kwargs["model"] = model
        else:
            from xbot.config import settings
            kwargs["model"] = getattr(settings, "MODEL_MAIN_CREATIVE", "litellm/deepseek-v4-pro-0813")

        if response_schema:
            kwargs["response_format"] = {"type": "json_object"}

        response = await self._client.chat.completions.create(**kwargs)
        content = response.choices[0].message.content or ""
        return content.strip()

    async def generate_image(self, prompt: str, **kwargs: Any) -> bytes:
        aspect_ratio = kwargs.get("aspect_ratio", "1:1")
        output_path = kwargs.get("output_path")
        if output_path:
            saved_path = await generate_and_save_nvidia_image_async(prompt=prompt, aspect_ratio=aspect_ratio, output_path=output_path)
            if saved_path:
                with open(saved_path, "rb") as f:
                    return f.read()
            return b""
        result = await generate_nvidia_image_async(prompt=prompt, aspect_ratio=aspect_ratio)
        if isinstance(result, str):
            import base64
            try:
                return base64.b64decode(result)
            except Exception:
                return result.encode("utf-8")
        elif isinstance(result, bytes):
            return result
        return b""
