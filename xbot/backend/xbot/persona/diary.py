from __future__ import annotations

import logging
import re
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class DiaryManager:
    """
    Manages daily diary entries ("inner monologue") for personas.
    Stores logs in /data/profiles/{profile_id}/diary/{YYYY-MM-DD}.md.
    """

    def __init__(self, profile_dir: Path) -> None:
        self.profile_dir = profile_dir
        self.diary_dir = profile_dir / "diary"

    def _get_date_str(self) -> str:
        return datetime.utcnow().strftime("%Y-%m-%d")

    def append_entry(
        self,
        mood: str,
        what_i_did: str,
        what_i_learned: str,
        how_it_went: str,
        thoughts_for_next_time: str,
        session_num: int | None = None,
        date_str: str | None = None,
    ) -> Path:
        """
        Appends a structured session entry to the daily diary markdown file.
        Auto-detects session number if not explicitly provided.
        """
        self.diary_dir.mkdir(parents=True, exist_ok=True)
        if not date_str:
            date_str = self._get_date_str()

        diary_file = self.diary_dir / f"{date_str}.md"
        now_time_str = datetime.utcnow().strftime("%I:%M %p")

        # 1. Determine session number if not provided
        if session_num is None:
            session_num = 1
            if diary_file.exists():
                try:
                    content = diary_file.read_text(encoding="utf-8")
                    # Count existing "## Session X" headers
                    sessions = re.findall(r"^## Session (\d+)", content, re.MULTILINE)
                    if sessions:
                        session_num = max(int(s) for s in sessions) + 1
                except Exception as e:
                    logger.warning("Error parsing diary for session count: %s", e)

        # 2. Prepare file headers if file is new
        file_is_new = not diary_file.exists()
        header = ""
        if file_is_new:
            header = f"# Diary — {date_str}\n\n"

        # 3. Format the new session block
        # Ensure that inputs don't have leading/trailing whitespace
        # that breaks formatting.
        entry_block = f"""## Session {session_num} ({now_time_str})
**Mood:** {mood.strip()}
**What I did:**
{what_i_did.strip()}

**What I learned:**
{what_i_learned.strip()}

**How it went:**
{how_it_went.strip()}

**Thoughts for next time:**
{thoughts_for_next_time.strip()}

"""

        # 4. Append to file
        with diary_file.open("a", encoding="utf-8") as f:
            if file_is_new:
                f.write(header)
            f.write(entry_block)

        logger.info(
            "Appended Session %d diary entry for %s", session_num, date_str
        )
        return diary_file

    def get_recent_entries(self, limit: int = 3) -> list[dict[str, str]]:
        """
        Retrieves the last `limit` diary entries, sorted from newest to oldest.
        Returns a list of dicts: [{"date": "YYYY-MM-DD", "content": "..."}].
        """
        if not self.diary_dir.exists():
            return []

        # Find all YYYY-MM-DD.md files
        diary_files = sorted(
            [
                f
                for f in self.diary_dir.glob("*.md")
                if re.match(r"^\d{4}-\d{2}-\d{2}\.md$", f.name)
            ],
            key=lambda x: x.name,
            reverse=True,
        )

        entries: list[dict[str, str]] = []
        for file_path in diary_files[:limit]:
            try:
                date_str = file_path.stem
                content = file_path.read_text(encoding="utf-8")
                entries.append({"date": date_str, "content": content})
            except Exception as e:
                logger.error("Failed to read diary file %s: %s", file_path, e)

        return entries
