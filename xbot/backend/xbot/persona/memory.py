from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class MemoryManager:
    """
    Manages episodic, semantic, and high-importance memories for a persona.
    Saves and reads from JSONL files under /data/profiles/{profile_id}/memories/.
    """

    def __init__(self, profile_dir: Path) -> None:
        self.profile_dir = profile_dir
        self.memories_dir = profile_dir / "memories"

    def _get_ts_str(self) -> str:
        return datetime.utcnow().isoformat() + "Z"

    def _append_to_jsonl(self, filepath: Path, record: dict[str, Any]) -> None:
        """Appends a single JSON record to the specified file."""
        self.memories_dir.mkdir(parents=True, exist_ok=True)
        try:
            with filepath.open("a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.error("Failed to append memory record to %s: %s", filepath, e)

    def _read_all_from_jsonl(self, filepath: Path) -> list[dict[str, Any]]:
        """Reads all JSON records from a JSONL file."""
        if not filepath.exists():
            return []
        records: list[dict[str, Any]] = []
        try:
            with filepath.open(encoding="utf-8") as f:
                for idx, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        records.append(json.loads(line))
                    except json.JSONDecodeError as jde:
                        logger.warning(
                            "Skipping invalid JSON line %d in %s: %s",
                            idx,
                            filepath.name,
                            jde,
                        )
        except Exception as e:
            logger.error("Failed to read JSONL file %s: %s", filepath, e)
        return records

    def append_episodic(
        self,
        event: str,
        content: str,
        importance: float,
        tweet_id: str | None = None,
        outcome: str | None = None,
    ) -> None:
        """Appends an episodic memory (events that happened)."""
        record = {
            "ts": self._get_ts_str(),
            "type": "episodic",
            "event": event,
            "content": content,
            "tweet_id": tweet_id,
            "outcome": outcome,
            "importance": importance,
        }
        self._append_to_jsonl(self.memories_dir / "episodic.jsonl", record)

    def append_semantic(
        self,
        fact: str,
        source: str,
        confidence: float,
        importance: float,
    ) -> None:
        """Appends a semantic memory (things learned/facts)."""
        record = {
            "ts": self._get_ts_str(),
            "type": "semantic",
            "fact": fact,
            "source": source,
            "confidence": confidence,
            "importance": importance,
        }
        self._append_to_jsonl(self.memories_dir / "semantic.jsonl", record)

    def append_important(
        self,
        content: str,
        evidence: str,
        importance: float,
    ) -> None:
        """Appends a persistent high-importance memory."""
        record = {
            "ts": self._get_ts_str(),
            "type": "important",
            "content": content,
            "evidence": evidence,
            "importance": importance,
        }
        self._append_to_jsonl(self.memories_dir / "important.jsonl", record)

    def retrieve_memories(
        self,
        recency_limit: int = 50,
        min_importance: float = 0.8,
        mention_query: str | None = None,
        token_budget: int = 4000,
    ) -> list[dict[str, Any]]:
        """
        Retrieves a compiled list of memories based on recency, importance, and query.
        Limits total memory size based on a token budget and returns
        chronologically sorted results.
        """
        # 1. Load memories from all sources
        episodic_all = self._read_all_from_jsonl(self.memories_dir / "episodic.jsonl")
        semantic_all = self._read_all_from_jsonl(self.memories_dir / "semantic.jsonl")
        important_all = self._read_all_from_jsonl(self.memories_dir / "important.jsonl")

        # 2. Select recent episodic memories
        recent_episodic = episodic_all[-recency_limit:] if recency_limit > 0 else []

        # Combine all candidates for filtering
        candidates: list[dict[str, Any]] = []
        candidates.extend(episodic_all)
        candidates.extend(semantic_all)
        candidates.extend(important_all)

        # Unique key helper to deduplicate candidates
        def _get_unique_key(m: dict[str, Any]) -> str:
            # Fallbacks for fields in different memory types
            content = m.get("content") or m.get("fact") or ""
            return f"{m.get('ts')}_{m.get('type')}_{content}"

        seen_keys = set()
        deduped_candidates: list[dict[str, Any]] = []
        for c in candidates:
            k = _get_unique_key(c)
            if k not in seen_keys:
                seen_keys.add(k)
                deduped_candidates.append(c)

        # 3. Filter candidates based on criteria
        filtered_memories: list[dict[str, Any]] = []
        for m in deduped_candidates:
            importance = m.get("importance", 0.0)

            # Rule 1: Always keep recent episodic (they were added from recent_episodic)
            is_recent_episodic = m in recent_episodic

            # Rule 2: Keep if high importance
            is_high_importance = importance >= min_importance

            # Rule 3: Keep if mentions query
            is_query_match = False
            if mention_query:
                q = mention_query.lower()
                # Search all string fields
                for _, v in m.items():
                    if isinstance(v, str) and q in v.lower():
                        is_query_match = True
                        break

            if is_recent_episodic or is_high_importance or is_query_match:
                filtered_memories.append(m)

        # 4. Truncate based on token budget
        # Sort candidate selection by importance desc to preserve most critical info
        filtered_memories.sort(key=lambda x: x.get("importance", 0.0), reverse=True)

        selected_memories: list[dict[str, Any]] = []
        current_token_estimate = 0

        for m in filtered_memories:
            # Estimate tokens: ~4 characters per token
            serialized = json.dumps(m, ensure_ascii=False)
            estimated_tokens = len(serialized) // 4
            if current_token_estimate + estimated_tokens <= token_budget:
                selected_memories.append(m)
                current_token_estimate += estimated_tokens
            else:
                # Exceeded budget, discard lower importance ones
                continue

        # 5. Sort chronologically ascending for standard context building
        selected_memories.sort(key=lambda x: x.get("ts", ""))
        return selected_memories
