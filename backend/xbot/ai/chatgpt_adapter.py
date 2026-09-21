"""
OpenAI-compatible Remote Adapter for ChatGPT Web Bridge.

Communicates over async HTTP with the standalone ChatGPT Bridge container
(e.g., http://192.168.0.200:8465), offloading heavy Chromium execution and
eliminating in-process browser memory leaks from Celery workers.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from typing import Any, TypeVar

import httpx
from pydantic import BaseModel

from xbot.config import settings

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

# Legacy backward-compatibility lock
_bridge_lock = asyncio.Lock()


def get_bridge_url() -> str:
    """Returns the configured bridge base URL stripped of trailing slash."""
    raw = getattr(settings, "CHATGPT_BRIDGE_URL", "http://192.168.0.200:8465")
    return (raw or "http://192.168.0.200:8465").strip().rstrip("/")


def reset_chatgpt_instance() -> None:
    """Legacy stub kept for backward compatibility."""
    pass


def get_chatgpt_instance() -> Any:
    """Legacy stub returning a facade client."""
    return ChatGPTBridgeAdapter()


class MockMessage:
    def __init__(self, content: str, parsed: Any | None = None) -> None:
        self.content = content
        self.parsed = parsed


class MockChoice:
    def __init__(self, content: str, parsed: Any | None = None) -> None:
        self.message = MockMessage(content, parsed)
        self.finish_reason = "stop"


class MockChatCompletion:
    def __init__(self, content: str, parsed: Any | None = None) -> None:
        self.choices = [MockChoice(content, parsed)]


def _format_messages_to_prompt(messages: list[dict[str, Any]]) -> str:
    """Combines OpenAI-style system and user messages into a unified prompt."""
    parts = []
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if role == "system":
            parts.append(f"=== INSTRUCTIONS & SYSTEM DIRECTIVES ===\n{content}\n")
        elif role == "user":
            parts.append(f"{content}\n")
        elif role == "assistant":
            parts.append(f"=== ASSISTANT CONTEXT ===\n{content}\n")
    return "\n".join(parts).strip()


def _extract_json_payload(text: str) -> dict[str, Any]:
    """Extracts JSON dict from raw markdown or codeblock text."""
    clean = text.strip()
    if "```json" in clean:
        clean = clean.split("```json", 1)[1].split("```", 1)[0].strip()
    elif "```" in clean:
        clean = clean.split("```", 1)[1].split("```", 1)[0].strip()

    # Try direct parse
    try:
        return json.loads(clean)
    except json.JSONDecodeError:
        pass

    # Regex search for first matching brace block
    match = re.search(r"\{[\s\S]*\}", clean)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    raise ValueError(f"Could not parse valid JSON from ChatGPT response: {text[:200]}")


class ChatGPTBridgeCompletions:
    """Handles chat completions via the remote ChatGPT Bridge container."""

    def __init__(self, is_beta: bool = False) -> None:
        self.is_beta = is_beta

    async def _post_prompt(self, prompt: str, model: str = "auto", timeout_s: float | None = None) -> str:
        """Sends a prompt to the remote ChatGPT bridge and extracts generated text."""
        bridge_url = get_bridge_url()
        timeout = timeout_s or float(getattr(settings, "CHATGPT_BRIDGE_TIMEOUT", 180.0))

        use_thinking = False
        if any(kw in str(model).lower() for kw in ("think", "reason", "sol", "o3")):
            use_thinking = True

        payload = {
            "prompt": prompt,
            "thinking": use_thinking,
            "model": "chatgpt-thinking" if use_thinking else "chatgpt",
        }

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.post(f"{bridge_url}/api/ask", json=payload)
                if resp.status_code != 200:
                    err_text = resp.text[:300]
                    raise RuntimeError(f"ChatGPT bridge returned HTTP {resp.status_code}: {err_text}")
                data = resp.json()
                text = data.get("text") or data.get("response", "")
                if not text:
                    raise RuntimeError(f"ChatGPT bridge returned empty response payload: {data}")
                return text.strip()
        except httpx.ConnectError as ce:
            logger.warning("ChatGPT bridge connection refused at %s: %s", bridge_url, ce)
            raise RuntimeError(f"ChatGPT bridge offline at {bridge_url}") from ce
        except httpx.TimeoutException as te:
            logger.warning("ChatGPT bridge request timed out after %.1fs at %s", timeout, bridge_url)
            raise RuntimeError(f"ChatGPT bridge timed out ({timeout}s)") from te
        except Exception as exc:
            logger.warning("ChatGPT bridge call error: %s", exc)
            raise RuntimeError(f"ChatGPT bridge failure: {exc}") from exc

    async def create(
        self,
        model: str = "auto",
        messages: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> MockChatCompletion:
        """Sends a standard text completion prompt to remote ChatGPT."""
        prompt = _format_messages_to_prompt(messages or [])
        text = await self._post_prompt(prompt, model=model)
        return MockChatCompletion(content=text)

    async def parse(
        self,
        model: str = "auto",
        messages: list[dict[str, Any]] | None = None,
        response_format: Any = None,
        **kwargs: Any,
    ) -> MockChatCompletion:
        """Sends a structured completion prompt and validates JSON response into response_format."""
        schema_instruction = ""
        if response_format and issubclass(response_format, BaseModel):
            schema_json = json.dumps(response_format.model_json_schema(), indent=2)
            schema_instruction = (
                "\n\nIMPORTANT: You must return ONLY a JSON object that adheres strictly to this schema:\n"
                f"```json\n{schema_json}\n```\n"
                "Return ONLY the valid JSON with no introductory or trailing text."
            )

        prompt = _format_messages_to_prompt(messages or []) + schema_instruction
        text = await self._post_prompt(prompt, model=model)
        parsed_json = _extract_json_payload(text)

        parsed_instance = None
        if response_format and issubclass(response_format, BaseModel):
            parsed_instance = response_format.model_validate(parsed_json)
        else:
            parsed_instance = parsed_json

        return MockChatCompletion(content=text, parsed=parsed_instance)


class ChatGPTBridgeAdapter:
    """
    OpenAI-compatible facade exposing `.chat.completions` and `.beta.chat.completions`.
    """

    def __init__(self) -> None:
        self.chat = ChatGPTBridgeAdapter.Chat()
        self.beta = ChatGPTBridgeAdapter.Beta()

    class Chat:
        def __init__(self) -> None:
            self.completions = ChatGPTBridgeCompletions(is_beta=False)

    class Beta:
        def __init__(self) -> None:
            self.chat = ChatGPTBridgeAdapter.BetaChat()

    class BetaChat:
        def __init__(self) -> None:
            self.completions = ChatGPTBridgeCompletions(is_beta=True)
