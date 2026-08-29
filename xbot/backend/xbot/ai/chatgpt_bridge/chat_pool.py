"""Bounded chat pool: keep the ChatGPT account free of endless conversations.

The bridge creates a new conversation on every turn. To stop the account's
sidebar from filling up, we track the conversation IDs we created and, once
the pool exceeds ``max_chats``, soft-delete the oldest ones via the backend
API (``PATCH /backend-api/conversation/{id}`` with ``is_visible: false``).

State is persisted to a small JSON file so the pool survives restarts.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from .errors import ShapeChangedError

# State directory lives in the user's home (shared with browser.py).
STATE_DIR = Path(os.environ.get("CHATGPT_BRIDGE_STATE", "~/.chatgpt-bridge")).expanduser()
POOL_FILE = STATE_DIR / "chat_pool.json"

DEFAULT_MAX_CHATS = 10


class ChatPoolManager:
    """Track bridge-created conversations and prune the oldest past a limit.

    ``session`` must expose ``get_access_token()`` / ``get_cookies()`` (the
    :class:`SessionManager` interface) and ``delete_conversation(id)`` (the
    :class:`BackendClient` interface). In practice the caller passes the
    :class:`BackendClient` itself, which satisfies both.
    """

    def __init__(
        self,
        session: Any,
        state_path: Path | str = POOL_FILE,
        max_chats: int = DEFAULT_MAX_CHATS,
    ) -> None:
        self.session = session
        self.state_path = Path(state_path)
        self.max_chats = max_chats
        self._ids: list[str] = self._load()

    def _load(self) -> list[str]:
        if not self.state_path.exists():
            return []
        try:
            data = json.loads(self.state_path.read_text())
            ids = data.get("ids", []) if isinstance(data, dict) else data
            return [str(i) for i in ids]
        except (json.JSONDecodeError, OSError):
            return []

    def _save(self) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.state_path.write_text(json.dumps({"ids": self._ids}))

    def record(self, conversation_id: str) -> None:
        """Record a conversation created by the bridge (most recent last)."""
        if not conversation_id:
            return
        # De-duplicate: move an existing id to the end (most recent).
        if conversation_id in self._ids:
            self._ids.remove(conversation_id)
        self._ids.append(conversation_id)
        self._save()

    async def prune(self) -> list[str]:
        """Delete the oldest conversations past ``max_chats``.

        Returns the list of conversation IDs that were deleted. Deletion
        failures are logged but do not raise (pruning is best-effort).
        """
        overflow = len(self._ids) - self.max_chats
        if overflow <= 0:
            return []

        to_delete = self._ids[:overflow]
        self._ids = self._ids[overflow:]
        self._save()

        deleted: list[str] = []
        for cid in to_delete:
            try:
                await self.session.delete_conversation(cid)
                deleted.append(cid)
            except ShapeChangedError:
                # Best-effort: keep going; the id is already dropped from the
                # pool so we won't retry it forever.
                continue
        return deleted