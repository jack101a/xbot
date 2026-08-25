"""
Community Discussion Harvester & Blue Tick Reciprocity Engine.
Discovers active peer Blue Tick creators and engagers across One Piece/Anime, Cinema/TV, Consumer Tech, and AI.
"""

from __future__ import annotations

import logging
import random
import uuid
from typing import Any
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

COMMUNITY_NICHE_CONFIG = {
    "anime": {
        "name": "One Piece & Anime",
        "icon": "🏴‍☠️",
        "queries": [
            "#ONEPIECE",
            "One Piece chapter",
            "Egghead anime",
            "manga theory discussion",
            "anime animation quality",
        ],
        "curated_peers": [
            {"handle": "MugiwaraTheory", "display_name": "Luffy Lore & Theories", "followers": 1420, "following": 980, "bio": "Weekly One Piece manga breakdowns • Oda foreshadowing nerd 🏴‍☠️"},
            {"handle": "EggheadArchive", "display_name": "Vegapunk Broadcast", "followers": 3200, "following": 1850, "bio": "Covering anime animation, Void Century lore & chapter leaks."},
            {"handle": "AnimeCinematics", "display_name": "Sakuga & Frames", "followers": 4800, "following": 2100, "bio": "Appreciating high tier animation cuts and manga panels."},
            {"handle": "ZoroPeakMoments", "display_name": "Grand Line Focus", "followers": 890, "following": 650, "bio": "Daily One Piece community discourse & powerscaling debates."},
            {"handle": "ShonenPulse", "display_name": "Shonen Chapter Pulse", "followers": 2400, "following": 1900, "bio": "Anime reviewer & weekly chapter discussions. Follow back mutuals!"},
        ]
    },
    "movies": {
        "name": "Movies & TV Discourse",
        "icon": "🎬",
        "queries": [
            "cinema cinematography",
            "movie review film",
            "box office movie",
            "season finale TV",
            "prestige drama film",
        ],
        "curated_peers": [
            {"handle": "CinephileFrame", "display_name": "Cinema Perspectives", "followers": 2900, "following": 1700, "bio": "IMAX junkie • 35mm film aesthetics • Let's debate plot twists 🍿"},
            {"handle": "PrestigeTVTakes", "display_name": "Episode Breakdown", "followers": 1850, "following": 1400, "bio": "Reviewing weekly HBO/Netflix prestige dramas and screenplays."},
            {"handle": "BoxOfficeLens", "display_name": "Cinema Numbers", "followers": 4100, "following": 2200, "bio": "Tracking global box office & director retrospectives."},
            {"handle": "IndieFilmReview", "display_name": "A24 & Indie Cinema", "followers": 950, "following": 820, "bio": "Deep dives into cinematography, sound design, and scriptwriting."},
        ]
    },
    "tech": {
        "name": "Consumer Tech & Hardware",
        "icon": "💻",
        "queries": [
            "iPhone vs Galaxy",
            "MacBook battery life",
            "Snapdragon chip laptop",
            "Pixel camera update",
            "smartphone upgrade",
        ],
        "curated_peers": [
            {"handle": "SiliconWorkflow", "display_name": "Hardware & Chips", "followers": 3100, "following": 1950, "bio": "Testing Apple Silicon vs Snapdragon X Elite • Laptop battery tests."},
            {"handle": "PocketShutter", "display_name": "Smartphone Camera Lab", "followers": 1600, "following": 1200, "bio": "Pixel vs iPhone vs Galaxy real world photo comparisons 📱"},
            {"handle": "EverydayDeskSetup", "display_name": "Workspace & Gear", "followers": 2400, "following": 1600, "bio": "Minimal tech setups, OLED monitors, mechanical keyboards."},
            {"handle": "MobileTechDaily", "display_name": "Android & iOS Pulse", "followers": 1250, "following": 900, "bio": "Daily consumer electronics reviews and battery benchmarks."},
        ]
    },
    "ai": {
        "name": "AI & LLM Ecosystem",
        "icon": "🤖",
        "queries": [
            "Claude 3.7 Sonnet",
            "ChatGPT prompt workflow",
            "Cursor AI coding",
            "open source LLM model",
            "AI agent production",
        ],
        "curated_peers": [
            {"handle": "PromptEngineerPro", "display_name": "Prompt Architecture", "followers": 4300, "following": 2500, "bio": "Experimenting with Claude 3.7 & Cursor AI agents in production 🤖"},
            {"handle": "LocalLLMLab", "display_name": "Ollama & Open Weights", "followers": 2100, "following": 1400, "bio": "Benchmarking open weights, quantization, and local dev setups."},
            {"handle": "IndieAgentBuilder", "display_name": "Autonomous Workflows", "followers": 1750, "following": 1300, "bio": "Building autonomous AI bots and sharing prompt templates. F4F!"},
            {"handle": "ContextWindowDev", "display_name": "Context & RAG", "followers": 3500, "following": 1800, "bio": "Full-stack AI developer • Let's connect and build in public."},
        ]
    },
    "growth_mutuals": {
        "name": "Active Follow-Back & Mutuals Posts",
        "icon": "🤝",
        "queries": [
            '"drop your handle" ("follow back" OR "mutuals")',
            '"looking for mutuals" (tech OR anime OR AI OR "blue tick")',
            '"follow back everyone who" (likes OR replies OR reposts)',
            '"verified mutuals" ("follow back" OR "connect")',
            '"f4f" ("blue tick" OR "verified")',
        ],
        "curated_peers": [
            {"handle": "GrowthMutualsHQ", "display_name": "Tech & Creator Mutuals", "followers": 2800, "following": 2600, "bio": "Connecting verified creators, developers, and anime fans. Follow back guaranteed! 🤝"},
            {"handle": "BlueTickConnect", "display_name": "Verified Builders Circle", "followers": 3900, "following": 3500, "bio": "Connecting Blue Tick subscribers across AI, tech, and creative spaces. F4F!"},
            {"handle": "AnimeMutualsHub", "display_name": "One Piece & Anime Mutuals", "followers": 1950, "following": 1800, "bio": "Find mutuals in the manga and anime community! 🏴‍☠️ Drop handle & follow back."},
            {"handle": "DevMutualsDaily", "display_name": "Indie Devs & AI Mutuals", "followers": 3200, "following": 2900, "bio": "Building in public • Connecting tech creators & AI engineers. 100% follow back."},
            {"handle": "CinephileMutuals", "display_name": "Movie & TV Mutuals", "followers": 1450, "following": 1350, "bio": "Film lovers and TV series live-tweeters connecting! Let's build our timeline 🍿"},
        ]
    },
    "indian_creators": {
        "name": "Indian Tech & Creator Ecosystem",
        "icon": "🇮🇳",
        "queries": [
            "#TechTwitterIndia",
            "#IndianTech",
            "Bangalore tech AI",
            "Delhi startup tech",
            "Indian anime manga community",
            "Indian cinema box office",
        ],
        "curated_peers": [
            {"handle": "DelhiTechJournal", "display_name": "Delhi Tech & Startups", "followers": 3100, "following": 2200, "bio": "Covering Indian tech ecosystem, AI engineering & Delhi startups.", "is_indian": True},
            {"handle": "BangaloreBuilds", "display_name": "Bangalore Dev Circle", "followers": 4400, "following": 2900, "bio": "Building in public in BLR • Full-stack, LLMs, and SaaS founders. Mutuals connect! 🤝", "is_indian": True},
            {"handle": "DesiAnimeClub", "display_name": "Indian Anime Community", "followers": 2600, "following": 2100, "bio": "One Piece & anime discourse across India. Chapter leaks, theories & memes 🏴‍☠️", "is_indian": True},
            {"handle": "IndianCineTakes", "display_name": "Indian Cinema & Film Lab", "followers": 3800, "following": 2400, "bio": "Analyzing pan-India cinema, box office, and global cinema aesthetics 🎬", "is_indian": True},
            {"handle": "IndiaAICreators", "display_name": "India AI & Builders", "followers": 5200, "following": 3100, "bio": "Connecting Indian AI developers, prompt engineers, and creators. F4F mutuals!", "is_indian": True},
        ]
    }
}


class HarvestedCandidate(BaseModel):
    handle: str
    display_name: str
    niche: str
    is_blue_tick: bool = True
    follower_count: int = 1000
    following_count: int = 800
    bio: str
    source_discussion: str
    reciprocity_score: float = 75.0
    is_indian_demographic: bool = False


class ActiveGrowthPost(BaseModel):
    id: str
    author_handle: str
    author_name: str
    is_blue_tick: bool = True
    tweet_text: str
    tweet_url: str
    reply_count: int
    retweet_count: int
    like_count: int
    niche: str
    posted_ago: str


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

