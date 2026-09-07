from __future__ import annotations

# Re-export facade for backward compatibility
from xbot.safety.simcluster import (
    CANONICAL_PROFILES,
    HASHTAG_PATTERN,
    SimClusterAnchorProfile,
    SimClusterScoreResult,
    SimClusterTopicScorer,
    calculate_lexical_overlap,
    enforce_natural_entity_density,
)

__all__ = [
    "CANONICAL_PROFILES",
    "HASHTAG_PATTERN",
    "SimClusterAnchorProfile",
    "SimClusterScoreResult",
    "SimClusterTopicScorer",
    "calculate_lexical_overlap",
    "enforce_natural_entity_density",
]
