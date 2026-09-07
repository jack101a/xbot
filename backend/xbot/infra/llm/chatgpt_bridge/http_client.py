"""Direct HTTP client for the chatgpt.com backend-api (fast path)."""

from __future__ import annotations

import json
import uuid

import httpx

from .errors import AuthError, ShapeChangedError
from .session import SessionManager

BACKEND_URL = "https://chatgpt.com/backend-api/conversation"

# Chrome-like user agent to keep the backend happy.
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


class BackendClient:
    """POST prompts to the ChatGPT backend and parse the SSE response."""

    def __init__(self, session: SessionManager, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self.session = session
        self._transport = transport

    async def ask(
        self, prompt: str, conversation_id: str | None = None
    ) -> dict:
        """Send a prompt and return ``{"text", "conversation_id"}``.

        Raises :class:`ShapeChangedError` on any unexpected status/payload so
        the caller can fall back to the UI path.
        """
        access_token = await self.session.get_access_token()
        cookies = await self.session.get_cookies()

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "User-Agent": USER_AGENT,
        }
        body = {
            "action": "next",
            "messages": [
                {
                    "id": str(uuid.uuid4()),
                    "author": {"role": "user"},
                    "content": {
                        "content_type": "text",
                        "parts": [prompt],
                    },
                }
            ],
            "parent_message_id": str(uuid.uuid4()),
            "model": None,
            "conversation_id": conversation_id,
        }

        async with httpx.AsyncClient(
            headers=headers,
            cookies=_cookie_map(cookies),
            timeout=180.0,
            transport=self._transport,
        ) as client:
            try:
                resp = await client.post(BACKEND_URL, json=body)
            except httpx.HTTPError as exc:
                raise ShapeChangedError(f"backend request failed: {exc}") from exc

        if resp.status_code != 200:
            raise ShapeChangedError(
                f"backend returned status {resp.status_code}"
            )

        return _parse_sse(resp.text)


def _cookie_map(cookies: list[dict]) -> dict:
    """Flatten Playwright-style cookies into a name->value map."""
    return {c["name"]: c["value"] for c in cookies}


def _parse_sse(text: str) -> dict:
    """Parse the SSE-style response and extract the final assistant message."""
    final_text: str | None = None
    conversation_id: str | None = None

    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("data:"):
            continue
        payload = line[len("data:"):].strip()
        if not payload:
            continue
        try:
            obj = json.loads(payload)
        except json.JSONDecodeError as exc:
            raise ShapeChangedError(f"non-JSON SSE payload: {exc}") from exc

        message = obj.get("message")
        if not isinstance(message, dict):
            continue

        status = message.get("status")
        if status == "finished_successfully":
            parts = (
                (message.get("content") or {}).get("parts")
                if isinstance(message.get("content"), dict)
                else None
            )
            if isinstance(parts, list) and parts:
                final_text = parts[0]
            conversation_id = obj.get("conversation_id") or message.get(
                "conversation_id"
            )
            break

    if final_text is None:
        raise ShapeChangedError("no finished assistant message found in SSE")

    return {"text": final_text, "conversation_id": conversation_id or ""}