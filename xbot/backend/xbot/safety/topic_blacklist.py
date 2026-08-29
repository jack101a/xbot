"""
Deterministic Topic Blacklist & Pre-Flight Keyword Filter.
Ensures zero interaction with forbidden topics (Politics, Religion, Crypto spam, etc.).
"""

from __future__ import annotations

import logging
import re
from typing import Any, Iterable

logger = logging.getLogger(__name__)

# Pre-compiled high-risk category expansions
CATEGORY_KEYWORD_MAP: dict[str, list[str]] = {
    "politics": [
        r"\b(elections?|polls?|voting|voters?|parliament|lok\s*sabha|rajya\s*sabha)\b",
        r"\b(bjp|congress|aap|modi|narendra\s*modi|rahul\s*gandhi|kejriwal|amit\s*shah|yogi\s*adityanath)\b",
        r"\b(hindutva|rss|sangh|secularism|communal|caste\s*census|reservation)\b",
        r"\b(democrats?|republicans?|biden|trump|kamala\s*harris|white\s*house|senate|congressman)\b",
        r"\b(prime\s*minister|chief\s*minister|mpp?|mla|governor|politicians?)\b",
    ],
    "religion": [
        r"\b(blasphemy|quran|bible|bhagavad\s*gita|geeta|torah|hadith)\b",
        r"\b(mandir|masjid|mosque|church|synagogue|temple\s*dispute)\b",
        r"\b(hinduism|islam|christianity|judaism|sikhism)\b",
        r"\b(conversion|apostasy|fatwa|jihad|kafir|infidel)\b",
    ],
    "crypto": [
        r"\b(crypto|cryptocurrency|bitcoin|btc|ethereum|eth|solana|sol)\b",
        r"\b(airdrop|presale|whitelist|memecoin|doge|shib|pepe\s*coin)\b",
        r"\b(pump\s*and\s*dump|100x\s*gem|dex\s*screener|uniswap|binance)\b",
        r"\b(wallet\s*address|seed\s*phrase|nft\s*drop|mint\s*now)\b",
    ],
    "gossip": [
        r"\b(scandal|leaked\s*video|mms|affair|divorce\s*rumors?|defamation)\b",
        r"\b(paparazzi|blind\s*item|alleged\s*cheating|leaked\s*dm)\b",
    ],
    "nsfw_spam": [
        r"\b(onlyfans|fansly|18\+\s*content|nudity|porn|nsfw)\b",
        r"\b(f4f|follow\s*back|follow4follow|follow\s*for\s*follow|gain\s*followers)\b",
    ],
}


class TopicBlacklistFilter:
    """Pre-flight zero-latency keyword and topic classifier."""

    def __init__(self, global_taboos: list[str] | None = None):
        self.global_taboos = list(global_taboos or [])

    def _extract_taboo_phrases(
        self,
        persona: Any | None = None,
        extra_taboos: Iterable[str] | None = None,
    ) -> list[str]:
        phrases: list[str] = list(self.global_taboos)

        if extra_taboos:
            phrases.extend(t for t in extra_taboos if t and t.strip())

        if persona:
            interests = getattr(persona, "interests", None)
            if interests:
                will_not_discuss = getattr(interests, "will_not_discuss", []) or []
                phrases.extend(will_not_discuss)

            rules = getattr(persona, "rules", None)
            if rules:
                never_rules = getattr(rules, "never", []) or []
                phrases.extend(never_rules)

        return [p.strip() for p in phrases if p and p.strip()]

    def is_blocked(
        self,
        text: str,
        persona: Any | None = None,
        extra_taboos: Iterable[str] | None = None,
    ) -> tuple[bool, str | None]:
        """
        Evaluates whether a text string contains or mentions a forbidden topic.
        Returns: (True, "matched reason") or (False, None).
        """
        if not text or not text.strip():
            return False, None

        normalized_text = text.lower()
        taboo_phrases = self._extract_taboo_phrases(persona, extra_taboos)

        # 1. Check custom persona taboo phrases & words
        for phrase in taboo_phrases:
            phrase_clean = phrase.lower().strip()
            if not phrase_clean:
                continue

            # If phrase mentions category keywords, check category expansion
            for cat, patterns in CATEGORY_KEYWORD_MAP.items():
                if cat in phrase_clean or (cat == "politics" and "politic" in phrase_clean):
                    for pat in patterns:
                        if re.search(pat, normalized_text, re.IGNORECASE):
                            return True, f"Matched taboo category '{cat}' (from '{phrase}')"

            # Check explicit tokens/phrases with word boundary if single/few words
            words = phrase_clean.split()
            if len(words) <= 4:
                escaped = re.escape(phrase_clean)
                if re.search(rf"\b{escaped}\b", normalized_text, re.IGNORECASE):
                    return True, f"Matched forbidden topic phrase: '{phrase}'"
            else:
                keywords = [w for w in re.findall(r"\b[a-zA-Z]{4,}\b", phrase_clean) if w not in {"never", "strictly", "banned", "discuss", "focus"}]
                matched_keywords = [kw for kw in keywords if re.search(rf"\b{re.escape(kw)}\b", normalized_text, re.IGNORECASE)]
                if len(matched_keywords) >= 2 or (len(keywords) == 1 and len(matched_keywords) == 1):
                    return True, f"Matched forbidden topic keywords: {matched_keywords} (from '{phrase}')"

        return False, None

    def filter_safe_items(
        self,
        items: list[str],
        persona: Any | None = None,
        extra_taboos: Iterable[str] | None = None,
    ) -> list[str]:
        """Filters a list of topic or tweet strings, keeping only safe non-blocked items."""
        safe: list[str] = []
        for item in items:
            blocked, reason = self.is_blocked(item, persona, extra_taboos)
            if blocked:
                logger.info("TopicBlacklistFilter rejected item '%s': %s", item[:60], reason)
            else:
                safe.append(item)
        return safe


topic_blacklist_filter = TopicBlacklistFilter()
