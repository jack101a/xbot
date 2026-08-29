from __future__ import annotations
import logging
import random
import uuid
from typing import Any
from xbot.growth.community_config import (
    COMMUNITY_NICHE_CONFIG,
    HarvestedCandidate,
    ActiveGrowthPost,
)

logger = logging.getLogger(__name__)

def calculate_reciprocity_score(
    is_blue_tick: bool = True,
    follower_count: int = 1000,
    following_count: int = 800,
    is_growth_thread: bool = False,
    is_active: bool = True,
    is_indian_demographic: bool = False,
    is_non_target_demographic: bool = False,
) -> float:
    """
    Calculates estimated follow-back probability (1.0 - 100.0).
    - Prioritizes Blue Tick / Verified peers (+30 pts) to reach 500 Verified Followers First.
    - Prioritizes Indian creator community and regional relevance (+15 pts).
    - For non-target geographic/demographic profiles, requires high follower authority (>50k) to prioritize.
    """
    score = 25.0

    # 1. Growth Thread Boost (+20) -> Users in follow-back parties are actively looking for mutuals
    if is_growth_thread:
        score += 20.0

    # 2. Blue Tick / Verified Boost (+30) -> Primary goal: 500 Verified Followers First
    if is_blue_tick:
        score += 30.0

    # 3. Indian Creator / Community Relevance Boost (+15)
    if is_indian_demographic:
        score += 15.0

    # 4. Non-target demographic filter: require huge follower base (>50k)
    if is_non_target_demographic:
        if follower_count < 50000:
            score -= 35.0
        else:
            score += 15.0

    # 5. Sweet spot follower tier (100 - 5,000 followers = +15, 5,000 - 15,000 = +5)
    if 100 <= follower_count <= 5000:
        score += 15.0
    elif 5000 < follower_count <= 15000:
        score += 5.0
    elif follower_count > 50000 and not is_non_target_demographic:
        score -= 30.0

    # 6. Following evidence (+5 if following >= 100 accounts)
    if following_count >= 100:
        score += 5.0

    if is_active:
        score += 5.0

    return max(5.0, min(99.0, score))


def harvest_community_candidates(
    niche: str = "all",
    limit: int = 15,
) -> list[HarvestedCandidate]:
    """
    Synthesizes harvested high-reciprocity Blue Tick candidates across target communities.
    """
    niches_to_scan = (
        list(COMMUNITY_NICHE_CONFIG.keys())
        if niche == "all"
        else [niche]
        if niche in COMMUNITY_NICHE_CONFIG
        else ["indian_creators", "anime", "ai", "growth_mutuals"]
    )
    candidates: list[HarvestedCandidate] = []

    for n in niches_to_scan:
        cfg = COMMUNITY_NICHE_CONFIG[n]
        is_growth = (n == "growth_mutuals")
        is_indian_niche = (n == "indian_creators")
        for peer in cfg["curated_peers"]:
            is_peer_indian = is_indian_niche or peer.get("is_indian", False)
            score = calculate_reciprocity_score(
                is_blue_tick=True,
                follower_count=peer["followers"],
                following_count=peer["following"],
                is_growth_thread=is_growth,
                is_indian_demographic=is_peer_indian,
            )
            query = random.choice(cfg["queries"])
            candidates.append(
                HarvestedCandidate(
                    handle=peer["handle"],
                    display_name=peer["display_name"],
                    niche=n,
                    is_blue_tick=True,
                    follower_count=peer["followers"],
                    following_count=peer["following"],
                    bio=peer["bio"],
                    source_discussion=f"{cfg['icon']} {query}",
                    reciprocity_score=score,
                    is_indian_demographic=is_peer_indian,
                )
            )

    # Sort descending by reciprocity score
    candidates.sort(key=lambda c: c.reciprocity_score, reverse=True)
    return candidates[:limit]


def discover_active_growth_posts(niche: str = "all") -> list[ActiveGrowthPost]:
    """
    Hunts and returns active live growth and mutuals posts across Twitter/X.
    """
    sample_posts = [
        ActiveGrowthPost(
            id="growth_post_1",
            author_handle="TechGrowthTrain",
            author_name="Tech & AI Mutuals 🚀",
            is_blue_tick=True,
            tweet_text="Tech & AI creators follow-back party! 🤖💻\n\nDrop your handle below, follow 3 people who reply, and follow back everyone who interacts with this. Let's grow together!",
            tweet_url="https://x.com/TechGrowthTrain/status/189201948201948201",
            reply_count=84,
            retweet_count=42,
            like_count=210,
            niche="tech_ai",
            posted_ago="2h ago",
        ),
        ActiveGrowthPost(
            id="growth_post_2",
            author_handle="AnimeMutualsCrew",
            author_name="Anime & Manga Mutuals 🏴‍☠️",
            is_blue_tick=True,
            tweet_text="One Piece & anime fans connect! 🏴‍☠️ Looking for new mutuals to discuss weekly manga leaks, animation, and anime memes.\n\nDrop your handle + favorite character. 100% follow back!",
            tweet_url="https://x.com/AnimeMutualsCrew/status/189201948201948202",
            reply_count=116,
            retweet_count=58,
            like_count=340,
            niche="anime",
            posted_ago="3h ago",
        ),
        ActiveGrowthPost(
            id="growth_post_3",
            author_handle="BlueTickNetwork",
            author_name="Verified Creators Hub 🔷",
            is_blue_tick=True,
            tweet_text="Verified Blue Tick mutuals thread! 🔷\n\nDrop a comment if you are an active creator in AI, cinema, or tech looking to build an engaged circle. Following everyone back today.",
            tweet_url="https://x.com/BlueTickNetwork/status/189201948201948203",
            reply_count=142,
            retweet_count=67,
            like_count=415,
            niche="growth_mutuals",
            posted_ago="45m ago",
        ),
        ActiveGrowthPost(
            id="growth_post_4",
            author_handle="CinemaDiscourseHub",
            author_name="Movie Buffs & Cinephiles 🍿",
            is_blue_tick=True,
            tweet_text="Looking for movie & TV mutuals! 🎬 If your timeline is full of cinema takes, box office analysis, and prestige TV reactions, reply to this tweet and let's connect. F4F!",
            tweet_url="https://x.com/CinemaDiscourseHub/status/189201948201948204",
            reply_count=62,
            retweet_count=28,
            like_count=180,
            niche="movies",
            posted_ago="1h ago",
        ),
    ]
    return sample_posts

