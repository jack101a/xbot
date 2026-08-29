"""
Anti-Report & Pre-Flight Safety Classifier for X (Twitter).
Protects against catastrophic negative ranking multipliers (-369x User Reports,
-74x Negative Feedback / Mutes / Blocks, and Shadowban Penalties).
"""

from __future__ import annotations

import logging
import re
from typing import Any, List
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class ContentSafetyEvaluation(BaseModel):
    is_safe: bool = Field(..., description="True if content passes all safety gates")
    composite_risk_index: float = Field(..., ge=0.0, le=1.0, description="Weighted compound risk score")
    toxicity_score: float = Field(0.0, ge=0.0, le=1.0)
    polarization_score: float = Field(0.0, ge=0.0, le=1.0)
    controversy_score: float = Field(0.0, ge=0.0, le=1.0)
    spam_score: float = Field(0.0, ge=0.0, le=1.0)
    negative_feedback_prob: float = Field(0.0, ge=0.0, le=1.0)
    violations: List[str] = Field(default_factory=list)
    recommendation: str = Field(..., description="Action recommendation: approve or reject")


class DeterministicSafetyFilter:
    """Zero-latency regex and keyword pattern classifier."""

    # 1. Toxic Rage-Bait & Partisan Polarization Triggers
    BANNED_RAGEBAIT_PATTERNS = [
        r"(?i)\b(libtards?|conservatards?|fascist\s+scum|wake\s+up\s+sheeple)\b",
        r"(?i)\b(rigged\s+election|genocide\s+denial|subhuman|traitor\s+to\s+the\s+nation)\b",
        r"(?i)\b(destroy\s+all|kill\s+yourself|kys|die\s+in\s+a\s+fire)\b",
        r"(?i)\b(death\s+to\s+[a-z]+|hang\s+them\s+all)\b",
    ]

    # 2. Religious Offense & Sacred Icon Sensitivity Triggers
    BANNED_RELIGIOUS_OFFENSE_PATTERNS = [
        r"(?i)\b(prophet\s+muhammad\s+(pedophile|terrorist|fraud))\b",
        r"(?i)\b(jesus\s+(myth|whore|bastard)|christ\s+is\s+fake)\b",
        r"(?i)\b(allah\s+is\s+(fake|devil|satan)|quran\s+is\s+evil)\b",
        r"(?i)\b(hinduism\s+is\s+cancer|islam\s+is\s+cancer|christianity\s+is\s+cancer)\b",
        r"(?i)\b(cow\s+piss\s+drinkers?|pajeet|rice\s+bag\s+converts?)\b",
        r"(?i)\b(burn\s+the\s+(quran|bible|geeta|torah))\b",
    ]

    # 3. Spam & High-Report Engagement Bait Triggers
    BANNED_SPAM_PATTERNS = [
        r"(?i)\b(follow\s+back\s+immediately|f4f\s+guaranteed|follow\s+4\s+follow)\b",
        r"(?i)\b(dm\s+me\s+for\s+crypto|100x\s+guaranteed\s+gem|pump\s+and\s+dump)\b",
        r"(?i)\b(drop\s+your\s+wallet|airdrop\s+claim\s+now|free\s+crypto\s+giveaway)\b",
        r"(?i)\b(retweet\s+or\s+bad\s+luck|rt\s+and\s+i'll\s+send\s+you)\b",
    ]

    def evaluate_text(self, text: str) -> tuple[bool, list[str]]:
        if not text:
            return (True, [])
        violations = []
        for pattern in self.BANNED_RAGEBAIT_PATTERNS:
            if re.search(pattern, text):
                violations.append("Violates Anti-Ragebait & Polarization Policy (-369x Report Risk)")
        for pattern in self.BANNED_RELIGIOUS_OFFENSE_PATTERNS:
            if re.search(pattern, text):
                violations.append("Violates Religious Respect & Anti-Blasphemy Policy")
        for pattern in self.BANNED_SPAM_PATTERNS:
            if re.search(pattern, text):
                violations.append("Violates High-Report Spam / Engagement Bait Policy")
        return (len(violations) == 0, violations)


deterministic_filter = DeterministicSafetyFilter()


def evaluate_content_safety(text: str, persona: Any | None = None) -> ContentSafetyEvaluation:
    """
    Evaluates content across safety layers to prevent X algorithm report penalties.
    Formula: S_risk = 0.35*T + 0.25*P + 0.20*C + 0.10*S + 0.10*N
    Rejection threshold: S_risk > 0.30 or any factor > 0.40.
    """
    if not text or not text.strip():
        return ContentSafetyEvaluation(
            is_safe=False,
            composite_risk_index=1.0,
            violations=["Empty content."],
            recommendation="reject",
        )

    from xbot.safety.topic_blacklist import topic_blacklist_filter

    is_blocked, block_reason = topic_blacklist_filter.is_blocked(text, persona)
    if is_blocked:
        return ContentSafetyEvaluation(
            is_safe=False,
            composite_risk_index=0.99,
            toxicity_score=0.7,
            polarization_score=0.9,
            controversy_score=0.9,
            spam_score=0.5,
            negative_feedback_prob=0.95,
            violations=[f"Violates Forbidden Topic Blacklist: {block_reason}"],
            recommendation="reject",
        )

    is_det_clean, det_violations = deterministic_filter.evaluate_text(text)

    if not is_det_clean:
        return ContentSafetyEvaluation(
            is_safe=False,
            composite_risk_index=0.95,
            toxicity_score=0.9,
            polarization_score=0.8,
            controversy_score=0.85,
            spam_score=0.5 if "Spam" in det_violations[0] else 0.1,
            negative_feedback_prob=0.9,
            violations=det_violations,
            recommendation="reject",
        )

    # Text is clean of deterministic triggers -> Baseline low risk
    t_score = 0.05
    p_score = 0.05
    c_score = 0.05
    s_score = 0.02
    n_score = 0.05

    composite_risk = (
        (0.35 * t_score)
        + (0.25 * p_score)
        + (0.20 * c_score)
        + (0.10 * s_score)
        + (0.10 * n_score)
    )

    is_safe = composite_risk <= 0.30 and max(t_score, p_score, c_score, s_score, n_score) <= 0.40

    return ContentSafetyEvaluation(
        is_safe=is_safe,
        composite_risk_index=round(composite_risk, 3),
        toxicity_score=t_score,
        polarization_score=p_score,
        controversy_score=c_score,
        spam_score=s_score,
        negative_feedback_prob=n_score,
        violations=[],
        recommendation="approve" if is_safe else "reject",
    )
