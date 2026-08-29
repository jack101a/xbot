from __future__ import annotations

import logging
from typing import Dict, List, Literal, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class SimClusterScoreResult(BaseModel):
    is_aligned: bool
    net_score: float = Field(..., description="Compound alignment score (0.0 to 1.0)")
    primary_similarity: float
    secondary_similarity: float
    negative_penalty: float
    detected_violations: List[str] = Field(default_factory=list)
    recommended_action: Literal["approve", "regenerate", "quarantine"]
    remediation_prompt: Optional[str] = None


class SimClusterAnchorProfile(BaseModel):
    profile_id: str
    simcluster_id: str
    cluster_name: str
    thresholds: Dict[str, float] = Field(
        default_factory=lambda: {
            "post_min_sim": 0.72,
            "visual_spec_min_sim": 0.70,
            "sniper_reply_min_sim": 0.62,
            "max_negative_leakage_sim": 0.35,
            "max_hashtags": 1.0,
        }
    )
    semantic_anchors_primary: List[str]
    semantic_anchors_secondary: List[str]
    anti_anchor_keywords: List[str]
    primary_centroid_embedding: Optional[List[float]] = None
    secondary_centroid_embedding: Optional[List[float]] = None
    negative_centroid_embeddings: List[List[float]] = Field(default_factory=list)


# Predefined Canonical Anchor Profiles for Core Niches
CANONICAL_PROFILES: Dict[str, SimClusterAnchorProfile] = {
    "delhi_lifestyle": SimClusterAnchorProfile(
        profile_id="kaya",
        simcluster_id="SC_41208_IN_DELHI_LIFESTYLE_CREATOR",
        cluster_name="Delhi Urban Lifestyle & Creator Sarcasm",
        semantic_anchors_primary=[
            "Hauz Khas Social",
            "Gurgaon Cyberhub",
            "Blinkit 10-minute grocery delivery",
            "Zomato Gold vs Swiggy One",
            "Delhi Metro Pink Line",
            "Aerocity cafe aesthetic",
            "Khan Market coffee prices",
            "Sarojini Nagar bargaining",
            "DLF Phase 5 apartment rent",
            "South Delhi accent and aesthetics",
            "Creator burnout and brand deals",
            "Delhi summer vs Delhi winter smog",
        ],
        semantic_anchors_secondary=[
            "Urban Indian dating app fatigue",
            "Overpriced matcha lattes",
            "Influencer podcast fatigue",
            "Weekend road trips to Rishikesh",
        ],
        anti_anchor_keywords=[
            "CUDA",
            "PyTorch",
            "Rust borrow checker",
            "Triton kernel",
            "vLLM",
            "Kubernetes",
            "FP8 quantization",
            "Airdrop",
            "Solana token",
            "Memecoin",
            "DEX liquidity",
            "Tokenomics",
            "One Piece chapter spoilers",
            "Joy Boy",
            "Gear 5",
            "Jujutsu Kaisen",
            "Sukuna",
        ],
    ),
    "ai_infra": SimClusterAnchorProfile(
        profile_id="techie_sarah",
        simcluster_id="SC_18492_GLOBAL_AI_INFRA_SYSTEMS",
        cluster_name="AI Infra, Distributed Systems & LLM Architecture",
        semantic_anchors_primary=[
            "vLLM token throughput",
            "Triton GPU kernels",
            "Speculative decoding latency",
            "Context window KV cache compression",
            "RAG chunking and vector indexing",
            "Postgres pgvector vs Qdrant",
            "ONNX Runtime inference deployment",
            "Quantization AWQ vs GGUF",
            "Distributed model training checkpoints",
        ],
        semantic_anchors_secondary=[
            "Solo founder SaaS architecture",
            "Developer tooling ergonomics",
            "Open source AI model licensing",
            "Engineering benchmarks",
        ],
        anti_anchor_keywords=[
            "Blinkit",
            "Zomato",
            "Sarojini Nagar",
            "Hauz Khas",
            "Delhi metro",
            "Luffy",
            "Zoro",
            "Straw Hat",
            "Anime episode breakdown",
            "Manga leaks",
            "100x gem",
            "Airdrop farming",
        ],
    ),
    "anime_lore": SimClusterAnchorProfile(
        profile_id="strawhat_lore",
        simcluster_id="SC_89411_GLOBAL_ANIME_ONEPIECE_SHONEN",
        cluster_name="Anime, One Piece Lore & Shonen Theory",
        semantic_anchors_primary=[
            "Joy Boy and the Void Century",
            "Eiichiro Oda foreshadowing",
            "Egghead Island lore revelations",
            "Advanced Conqueror's Haki scaling",
            "Ancient Weapons Uranus and Pluton",
            "Toei Animation sakuga direction",
            "Weekly Shonen Jump chapter analysis",
        ],
        semantic_anchors_secondary=[
            "Jujutsu Kaisen domain expansion mechanics",
            "Chainsaw Man devil contracts",
            "Bleach Thousand-Year Blood War pacing",
        ],
        anti_anchor_keywords=[
            "B2B SaaS",
            "vLLM",
            "Postgres",
            "Seed round funding",
            "ARR metrics",
            "API gateway",
            "Gurgaon traffic",
            "Blinkit grocery",
            "Delhi rent",
            "Khan Market",
        ],
    ),
}
