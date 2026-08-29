from __future__ import annotations

import logging
import re
from typing import List, Literal, Optional

from .clusters import (
    SimClusterAnchorProfile,
    SimClusterScoreResult,
)

logger = logging.getLogger(__name__)

HASHTAG_PATTERN = re.compile(r"#([A-Za-z0-9_]+)")


def enforce_natural_entity_density(text: str, max_hashtags: int = 1) -> str:
    """
    Enforces the 0-1 hashtag ceiling by seamlessly converting excess hashtags
    into natural inline English words, eliminating the downstream spam penalty.
    """
    if not text:
        return text

    matches = list(HASHTAG_PATTERN.finditer(text))
    if len(matches) <= max_hashtags:
        return text

    cleaned = text
    preserved_count = 0

    for match in reversed(matches):
        if preserved_count < max_hashtags:
            preserved_count += 1
            continue
        tag_start, tag_end = match.span()
        raw_word = match.group(1)
        cleaned = cleaned[:tag_start] + raw_word + cleaned[tag_end:]

    cleaned = re.sub(r"[ \t]+", " ", cleaned).strip()
    return cleaned


def calculate_lexical_overlap(text: str, anchor_phrases: List[str]) -> float:
    """Calculates normalized entity token overlap between text and anchor phrases."""
    if not text or not anchor_phrases:
        return 0.0
    text_lower = text.lower()
    matches = 0.0
    for phrase in anchor_phrases:
        words = phrase.lower().split()
        if all(w in text_lower for w in words):
            matches += 1.0
        elif any(w in text_lower for w in words if len(w) > 4):
            matches += 0.5
    return min(1.0, matches / max(2.0, len(anchor_phrases) * 0.3))


class SimClusterTopicScorer:
    """
    Validates synthesized posts and sniper replies against active SimCluster boundaries
    to prevent KnownFor vector dilution in X's 145,000 cluster spaces.
    """

    def __init__(self, profile_anchor: SimClusterAnchorProfile):
        self.profile = profile_anchor
        self._compile_regex_filters()

    def _compile_regex_filters(self) -> None:
        """Compiles regex boundary patterns for zero-latency lexical scanning."""
        escaped_negatives = [
            re.escape(kw) for kw in self.profile.anti_anchor_keywords if kw.strip()
        ]
        if escaped_negatives:
            pattern_str = r"(?i)\b(" + "|".join(escaped_negatives) + r")\b"
            self.anti_anchor_regex: Optional[re.Pattern[str]] = re.compile(pattern_str)
        else:
            self.anti_anchor_regex = None

    def validate_content(
        self,
        text: str,
        content_type: Literal["post", "visual_spec", "sniper_reply"] = "post",
        custom_embedding: Optional[List[float]] = None,
    ) -> SimClusterScoreResult:
        """
        Executes multi-stage validation against active SimCluster profile.
        """
        violations: List[str] = []
        cleaned_text = text.strip() if text else ""

        if not cleaned_text:
            return SimClusterScoreResult(
                is_aligned=False,
                net_score=0.0,
                primary_similarity=0.0,
                secondary_similarity=0.0,
                negative_penalty=0.0,
                detected_violations=["Empty content."],
                recommended_action="regenerate",
                remediation_prompt="Content is empty. Synthesize high-signal post aligned with niche.",
            )

        # -------------------------------------------------------------
        # Layer 1: Fast Regex & Lexicon Boundary Checks (<1ms)
        # -------------------------------------------------------------
        hashtags = HASHTAG_PATTERN.findall(cleaned_text)
        max_hashtags = int(self.profile.thresholds.get("max_hashtags", 1.0))
        if len(hashtags) > max_hashtags:
            violations.append(
                f"Hashtag spam detected ({len(hashtags)} found, max {max_hashtags}). "
                f"Modern X algorithm penalizes multiple hashtags. Enforce natural entity tokens."
            )

        if self.anti_anchor_regex:
            matches = self.anti_anchor_regex.findall(cleaned_text)
            if matches:
                violations.append(
                    f"Forbidden cross-niche entity detected: {list(set(matches))}. "
                    f"Causes instant KnownFor vector dilution into foreign clusters."
                )

        # -------------------------------------------------------------
        # Layer 2: Similarity Alignment Scorer (Lexical + Vector)
        # -------------------------------------------------------------
        primary_sim = calculate_lexical_overlap(
            cleaned_text, self.profile.semantic_anchors_primary
        )
        secondary_sim = calculate_lexical_overlap(
            cleaned_text, self.profile.semantic_anchors_secondary
        )
        negative_penalty = 0.0

        if self.anti_anchor_regex and self.anti_anchor_regex.search(cleaned_text):
            negative_penalty = 0.85

        # Compound score
        alpha, beta, gamma = 0.70, 0.30, 0.40
        net_score = (alpha * primary_sim) + (beta * secondary_sim) - (gamma * negative_penalty)
        net_score = max(0.0, min(1.0, net_score))

        is_aligned = len(violations) == 0
        action: Literal["approve", "regenerate", "quarantine"] = (
            "approve" if is_aligned else "regenerate"
        )

        remediation_prompt = None
        if not is_aligned:
            sample_entities = ", ".join(self.profile.semantic_anchors_primary[:4])
            remediation_prompt = (
                f"REJECTION REASON: {'; '.join(violations)}\n"
                f"ALIGNMENT INSTRUCTION: Lock copy strictly to SimCluster '{self.profile.cluster_name}'. "
                f"Weave in 2-3 authentic community entities such as: {sample_entities}. "
                f"Zero off-topic buzzwords. Maximum 0 to 1 hashtags."
            )

        return SimClusterScoreResult(
            is_aligned=is_aligned,
            net_score=round(net_score, 3),
            primary_similarity=round(primary_sim, 3),
            secondary_similarity=round(secondary_sim, 3),
            negative_penalty=round(negative_penalty, 3),
            detected_violations=violations,
            recommended_action=action,
            remediation_prompt=remediation_prompt,
        )
