from __future__ import annotations
from typing import Any
from pydantic import BaseModel, Field

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


