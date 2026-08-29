"""
OpenAI-compatible Adapter for ChatGPT Web Bridge.

Provides drop-in compatibility for AsyncOpenAI interfaces:
- client.chat.completions.create(...)
- client.beta.chat.completions.parse(...)

Uses asyncio.Lock to serialize turns and prevent tab collisions.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from typing import Any, TypeVar

from pydantic import BaseModel

from xbot.ai.chatgpt_bridge.core import ChatGPT
from xbot.ai.chatgpt_bridge.errors import (
    AuthError,
    BridgeTimeoutError,
    ShapeChangedError,
)
from xbot.config import settings

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

# Global lock & singleton instance
_bridge_lock = asyncio.Lock()
_bridge_instance: ChatGPT | None = None


def get_chatgpt_instance() -> ChatGPT:
    """Returns or creates the singleton ChatGPT web bridge instance."""
    global _bridge_instance
    if _bridge_instance is None:
        headless = getattr(settings, "CHATGPT_BRIDGE_HEADLESS", True)
        if not os.environ.get("DISPLAY"):
            headless = True
        if os.environ.get("PYTEST_CURRENT_TEST") or os.environ.get("CHATGPT_BRIDGE_HEADLESS") == "1":
            headless = True
        _bridge_instance = ChatGPT(headless=headless, auto_relogin=False)
    return _bridge_instance


def reset_chatgpt_instance() -> None:
    """Closes and resets the singleton instance (e.g. for testing)."""
    global _bridge_instance
    if _bridge_instance is not None:
        try:
            _bridge_instance.close()
        except Exception:
            pass
        _bridge_instance = None


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
    """Combines OpenAI-style system and user messages into a unified ChatGPT prompt."""
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
    """Handles chat completions via ChatGPT bridge."""

    def __init__(self, is_beta: bool = False) -> None:
        self.is_beta = is_beta

    async def create(
        self,
        model: str = "auto",
        messages: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> MockChatCompletion:
        """Sends a standard text completion prompt to ChatGPT."""
        prompt = _format_messages_to_prompt(messages or [])
        async with _bridge_lock:
            bridge = get_chatgpt_instance()
            try:
                res = await bridge.ask(prompt)
                text = res.get("text", "")
                return MockChatCompletion(content=text)
            except (AuthError, ShapeChangedError, BridgeTimeoutError) as e:
                logger.warning("ChatGPT bridge request error: %s", e)
                raise RuntimeError(f"ChatGPT bridge failure: {e}") from e

    async def parse(
        self,
        model: str = "auto",
        messages: list[dict[str, Any]] | None = None,
        response_format: Any = None,
        **kwargs: Any,
    ) -> MockChatCompletion:
        """Sends a structured completion prompt and parses the JSON response into response_format."""
        schema_instruction = ""
        if response_format and issubclass(response_format, BaseModel):
            schema_json = json.dumps(response_format.model_json_schema(), indent=2)
            schema_instruction = (
                "\n\nIMPORTANT: You must return ONLY a JSON object that adheres strictly to this schema:\n"
                f"```json\n{schema_json}\n```\n"
                "Return ONLY the valid JSON with no introductory or trailing text."
            )

        prompt = _format_messages_to_prompt(messages or []) + schema_instruction

        async with _bridge_lock:
            bridge = get_chatgpt_instance()
            try:
                res = await bridge.ask(prompt)
                text = res.get("text", "")
                parsed_json = _extract_json_payload(text)

                parsed_instance = None
                if response_format and issubclass(response_format, BaseModel):
                    parsed_instance = response_format.model_validate(parsed_json)
                else:
                    parsed_instance = parsed_json

                return MockChatCompletion(content=text, parsed=parsed_instance)
            except (AuthError, ShapeChangedError, BridgeTimeoutError) as e:
                logger.warning("ChatGPT bridge structured parse error: %s", e)
                raise RuntimeError(f"ChatGPT bridge parse failure: {e}") from e


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
