from __future__ import annotations

import json
import logging
from pathlib import Path
import random
import re
from typing import Any
from pydantic import BaseModel, Field

from xbot.ai.anti_ai_gatekeeper import strip_surrounding_quotes
from xbot.ai.client import get_ai_client
from xbot.ai.image_engine import generate_post_image_async
from xbot.config import settings
from xbot.persona.loader import Persona

logger = logging.getLogger(__name__)

BASE_GROWTH_ARCHETYPES = [
    "COMMUNITY_CONNECTION",      # High-energy call for creators, builders & peers in the niche to connect & follow
    "CREATOR_MUTUALS_CALL",      # Direct, authentic invitation to follow, connect as mutuals, and grow together
    "POLARIZING_DEBATE",        # Spicy dilemma or polarizing question with high reply & follow value
    "CREATOR_VIBE_CHECK",       # Relatable creator dilemma, workflow, or self-aware growth observation
    "MILESTONE_CELEBRATION",    # Journey to next follower milestone with call for peers to join the ride
    "AESTHETIC_SHOWCASE",       # Craft or tech appreciation paired with stunning 3D visual
    "CONTRARIAN_INSIGHT",       # Counter-intuitive take on growth/tools that earns bookmarks & follows
]
GROWTH_ARCHETYPES = BASE_GROWTH_ARCHETYPES

BASE_ARCHETYPE_PROMPTS = {
    "COMMUNITY_CONNECTION": (
        "An engaging, high-energy call to connect with fellow creators and builders on X. "
        "Ask what they are currently building, testing, or obsessed with. "
        "Make them feel seen and compelled to hit follow and drop a reply."
    ),
    "CREATOR_MUTUALS_CALL": (
        "An authentic, community-driven call to connect as mutuals and grow together on X. "
        "Deliver it with genuine creator enthusiasm, welcoming other active accounts to follow and interact."
    ),
    "POLARIZING_DEBATE": (
        "A thought-provoking, polarizing question or dilemma related to tech, creator craft, or digital culture "
        "where both sides have passionate defenders. Compels replies, quote tweets, and follows."
    ),
    "CREATOR_VIBE_CHECK": (
        "A sharp, relatable creator dilemma or witty observation about modern creative workflow, building in public, "
        "or audience growth. Deliver it with authentic creator wit."
    ),
    "MILESTONE_CELEBRATION": (
        "A motivating milestone update focused on reaching the next creator goal (e.g. 500 followers). "
        "Invites new followers to join the journey and connect with a growing creator."
    ),
    "AESTHETIC_SHOWCASE": (
        "A high-taste aesthetic commentary on visual craft, digital architecture, or hardware design. "
        "Pairs seamlessly with an innovative 3D conceptual visual."
    ),
    "CONTRARIAN_INSIGHT": (
        "A sharp, unexpected observation dissecting the gap between marketing hype and actual daily creator reality. "
        "High signal and practical framing that makes readers immediately bookmark and hit follow."
    ),
}

# User-specified growth hashtags
GROWTH_HASHTAG_POOL = [
    "#F4F",
    "#500Followers",
    "#FollowForFollow",
    "#FollowForFollowBack",
    "#FollowBack",
    "#FollowTrain",
    "#Mutuals",
    "#IFollowBack",
    "#TeamFollowBack",
]

GROWTH_LANGUAGES = ["english", "hinglish", "bilingual"]

CREATIVE_VISUAL_MOTIFS = [
    {
        "id": "NEURAL_COMMUNITY_GRAPH",
        "name": "Interconnected Community Constellation",
        "description": "3D glowing network nodes and luminous connection beams forming an ascending neural constellation on dark glassmorphism.",
    },
    {
        "id": "FUTURISTIC_METRIC_HUD",
        "name": "Holographic Telemetry & Milestone HUD",
        "description": "3D holographic telemetry display and laser-etched follower gauges with dynamic ascending metric arcs and neon telemetry rings.",
    },
    {
        "id": "ASCENDING_GLASS_LADDER",
        "name": "Surreal Floating Glass Staircase",
        "description": "Minimalist surreal 3D staircase of floating translucent glass platforms rising into a digital horizon with glowing milestone achievements.",
    },
    {
        "id": "HOLOGRAPHIC_ORBITAL_CORE",
        "name": "Orbital Mutuals Gyroscope",
        "description": "Futuristic 3D gyroscopic orbital device with concentric rotating metallic and glass rings orbiting a radiant energy core of mutual connections.",
    },
    {
        "id": "CYBERPUNK_SYNTHWAVE_RADAR",
        "name": "Cyberpunk Neon Creator Radar",
        "description": "Sleek 3D radar grid with neon wireframe terrain, sweeping beams scanning for creators, and a luminous horizon milestone.",
    },
    {
        "id": "CREATOR_STUDIO_ISOMETRIC",
        "name": "3D Isometric Creator Command Studio",
        "description": "Clean 3D isometric studio/command desk with floating holographic displays, illuminated creator tools, neon follow badge, and ambient lighting.",
    },
    {
        "id": "TACTILE_3D_PILL",
        "name": "Tactile Frosted Glass Interaction Pill",
        "description": "Tactile, ultra-premium 3D glowing interaction pill button reading 'Follow' or 'Connect' with floating notification sparks and particle vectors.",
    },
]

COLOR_PALETTES = [
    ("electric cyan", "neon violet"),
    ("radiant obsidian", "warm amber gold"),
    ("emerald neon", "mint green"),
    ("sunset magenta", "ultramarine blue"),
    ("ice blue", "platinum silver"),
]

POST_LENGTH_TIERS = {
    "ultra_punchy": {
        "id": "ultra_punchy",
        "name": "Ultra-Punchy & Direct",
        "description": "1 to 2 short lines maximum (under 90 characters total). Extreme brevity, hook straight into the CTA. Absolutely NO filler, NO backstory.",
        "char_limit": "under 90 chars",
    },
    "compact": {
        "id": "compact",
        "name": "Short & Compact",
        "description": "2 to 3 short lines (around 100-150 characters total). Crisp, scannable, quick conversational thought + call-to-action.",
        "char_limit": "100-150 chars",
    },
    "conversational": {
        "id": "conversational",
        "name": "Conversational Break",
        "description": "3 to 4 lines with clean mobile whitespace (around 160-230 characters total). Relatable creator observation + open question or CTA.",
        "char_limit": "160-230 chars",
    },
}


def sanitize_gender_neutrality(text: str) -> str:
    """
    Deterministically cleans any accidental gender admissions or gendered Hindi/Hinglish inflections
    to guarantee strict gender neutrality (never admitting or implying male or female).
    """
    replacements = [
        # Hindi/Hinglish gendered verbs to neutral equivalents
        (r'\b(?:karna\s+)?chahti\s+hoon\b', 'connect karna hai'),
        (r'\b(?:karna\s+)?chahta\s+hoon\b', 'connect karna hai'),
        (r'\bchahti\s+hoon\b', 'karna hai'),
        (r'\bchahta\s+hoon\b', 'karna hai'),
        (r'\bchahti\s+hai\b', 'chahiye'),
        (r'\bchahta\s+hai\b', 'chahiye'),
        (r'\bkarungi\b', 'karenge'),
        (r'\bkarunga\b', 'karenge'),
        (r'\bdekh\s+rahi\s+hoon\b', 'dekh rahe hain'),
        (r'\bdekh\s+raha\s+hoon\b', 'dekh rahe hain'),
        (r'\brahi\s+hoon\b', 'rahe hain'),
        (r'\braha\s+hoon\b', 'rahe hain'),
        (r'\bsochti\s+hoon\b', 'lagta hai'),
        (r'\bsochta\s+hoon\b', 'lagta hai'),
        (r'\bbolti\s+hoon\b', 'kehna hai'),
        (r'\bbolta\s+hoon\b', 'kehna hai'),
        (r'\bkarti\s+hoon\b', 'karte hain'),
        (r'\bkarta\s+hoon\b', 'karte hain'),
        # Gendered labels
        (r'\b(?:as\s+a\s+)(?:girl|guy|man|woman|female|male|boy)\b', 'as a creator'),
        (r'\bI(?:\'?m|\s+am)\s+(?:a\s+)?(?:girl|guy|man|woman|female|male|boy)\b', 'I am a creator'),
        (r'\b(?:ladka|ladki)\s+hoon\b', 'creator hoon'),
    ]
    cleaned = text
    for pattern, repl in replacements:
        cleaned = re.sub(pattern, repl, cleaned, flags=re.IGNORECASE)
    return cleaned


IDEAS_CACHE_FILE = Path("data/growth_research/f4f_growth_ideas.json")

FORBIDDEN_HUMAN_PATTERNS = [
    r'\b(?:photorealistic\s+)?(?:man|woman|men|women|person|people|female|male|girl|boy|guy|model|human|face|faces|portrait|hand|hands|crowd|creator\s+standing|creator\s+sitting)\b',
    r'\b(?:holding\s+(?:a|an|the)?\s*camera|looking\s+into\s+camera|selfie|studio\s+photograph\s+of)\b',
    r'\b(?:realistic\s+skin|human\s+skin|facial\s+features|caucasian|asian|african|latino|latina)\b',
]

FORBIDDEN_CINEMATIC_PATTERNS = [
    r'\b(?:cinematic\s+film\s+still|film\s+noir|moody\s+film\s+grain|cinematic\s+drama|brooding\s+shadows|gritty\s+film|movie\s+scene|cinematic\s+lighting)\b',
]


def load_discovered_growth_ideas() -> dict[str, Any]:
    """Loads dynamically discovered F4F post & 3D image ideas from X search analysis."""
    if not IDEAS_CACHE_FILE.exists():
        return {}
    try:
        data = json.loads(IDEAS_CACHE_FILE.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return data
    except Exception as e:
        logger.debug("Could not read discovered growth ideas from %s: %s", IDEAS_CACHE_FILE, e)
    return {}


def get_active_archetypes() -> tuple[list[str], dict[str, str]]:
    """Returns active growth archetypes merged with newly discovered X ideas."""
    archetypes = list(BASE_GROWTH_ARCHETYPES)
    prompts = dict(BASE_ARCHETYPE_PROMPTS)

    discovered = load_discovered_growth_ideas()
    custom_archetypes = discovered.get("discovered_archetypes", [])
    if isinstance(custom_archetypes, list):
        for item in custom_archetypes:
            if isinstance(item, dict) and item.get("name") and item.get("directive"):
                name = item["name"].strip().upper().replace(" ", "_")
                if name not in archetypes:
                    archetypes.append(name)
                prompts[name] = item["directive"].strip()

    return archetypes, prompts


def compute_next_milestone(current_followers: int) -> int:
    """
    Computes the next logical follower milestone based on current follower count.
    0..499 -> 500
    500..999 -> 1000
    1000..2499 -> 2500
    2500..4999 -> 5000
    5000..9999 -> 10000
    10000+ -> round up to next 5000
    """
    if current_followers < 500:
        return 500
    elif current_followers < 1000:
        return 1000
    elif current_followers < 2500:
        return 2500
    elif current_followers < 5000:
        return 5000
    elif current_followers < 10000:
        return 10000
    else:
        step = 5000
        return ((current_followers // step) + 1) * step


def enforce_hashtag_count(
    text: str,
    target_count: int,
    milestone_tag: str | None = None,
    fallback_tags: list[str] | None = None,
) -> str:
    """
    Deterministically guarantees that the post copy contains exactly `target_count` (0, 1, or 2)
    growth hashtags such as #F4F, #500Followers, #FollowForFollow, etc.
    """
    target_count = max(0, min(2, target_count))

    # Build available hashtag pool
    pool: list[str] = list(GROWTH_HASHTAG_POOL)
    if milestone_tag and milestone_tag not in pool:
        pool.insert(0, milestone_tag)

    discovered = load_discovered_growth_ideas()
    for tag in discovered.get("winning_hashtags", []):
        if tag.startswith("#") and tag not in pool:
            pool.append(tag)

    if fallback_tags:
        for ft in fallback_tags:
            if ft not in pool:
                pool.append(ft)

    # 1. Extract existing hashtags
    existing_tags = re.findall(r'#\w+', text)

    # Clean all hashtags from original text to reconstruct cleanly
    clean_text = re.sub(r'#\w+', '', text)
    clean_text = re.sub(r'[ \t]+(?=\n|$)', '', clean_text)
    clean_text = re.sub(r'[ \t]{2,}', ' ', clean_text).strip()

    if target_count == 0:
        return clean_text

    chosen_tags: list[str] = []
    # Preserve existing hashtags if any
    for tag in existing_tags:
        if len(chosen_tags) < target_count and tag not in chosen_tags:
            chosen_tags.append(tag)

    # Fill remaining from growth hashtag pool
    if len(chosen_tags) < target_count:
        shuffled = list(pool)
        if milestone_tag and milestone_tag in shuffled:
            shuffled.remove(milestone_tag)
            shuffled.insert(0, milestone_tag)
        else:
            random.shuffle(shuffled)

        for tag in shuffled:
            if len(chosen_tags) >= target_count:
                break
            if tag not in chosen_tags:
                chosen_tags.append(tag)

    tags_suffix = " ".join(chosen_tags)
    if clean_text:
        return f"{clean_text}\n\n{tags_suffix}"
    return tags_suffix


def sanitize_growth_image_prompt(
    prompt: str,
    include_milestone: bool = False,
    milestone_num: int = 500,
    fallback_prompt: str | None = None,
) -> str:
    """
    Guarantees:
    1. Zero realistic humans (male/female/faces/bodies).
    2. Growth & following visual theme (glowing 3D follow button, network nodes, trajectory, milestone badge).
    3. No heavy cinematic / film noir drama (clean modern 3D design, crisp studio lighting).
    """
    cleaned = prompt.strip()

    # 1. Scrub heavy cinematic / film noir drama
    for pat in FORBIDDEN_CINEMATIC_PATTERNS:
        cleaned = re.sub(pat, 'clean modern studio lighting', cleaned, flags=re.IGNORECASE)

    # 2. Scrub positive human depictions and photorealistic keywords
    positive_human_patterns = [
        r'\b(?:portrait\s+of\s+(?:a|an)?|photograph\s+of\s+(?:a|an)?)\s*[^,.;]*',
        r'\b(?:featuring\s+(?:a|an)?|showing\s+(?:a|an)?)\s*(?:photorealistic\s+)?(?:man|woman|person|human|model|girl|boy|face)[^,.;]*',
        r'\b(?:man|woman|person|human|girl|boy|model)\s+(?:standing|sitting|working|smiling|looking|holding)[^,.;]*',
        r'\b(?:photorealistic\s+human|realistic\s+skin|human\s+skin|facial\s+features)\b',
        r'\bphotorealistic\b',
    ]
    for pat in positive_human_patterns:
        cleaned = re.sub(pat, '', cleaned, flags=re.IGNORECASE)

    # Clean whitespace and punctuation
    cleaned = re.sub(r'[,;\s]{2,}', ', ', cleaned)
    cleaned = re.sub(r'\s{2,}', ' ', cleaned).strip(" ,;")

    # 3. Verify presence of growth/following signals
    has_growth_keywords = any(
        kw in cleaned.lower()
        for kw in [
            "follow", "growth", "network", "milestone", "connection",
            "nodes", "community", "trajectory", "momentum", "constellation",
            "orbital", "radar", "studio", "pill", "telemetry", "staircase"
        ]
    )

    if len(cleaned) < 30 or not has_growth_keywords:
        if fallback_prompt and len(fallback_prompt.strip()) >= 30:
            cleaned = fallback_prompt.strip()
        else:
            # Check if we have discovered image concepts from X research
            discovered = load_discovered_growth_ideas()
            concepts = discovered.get("discovered_image_concepts", [])
            if concepts and isinstance(concepts, list):
                chosen_c = random.choice(concepts)
                if isinstance(chosen_c, dict) and chosen_c.get("prompt"):
                    cleaned = chosen_c["prompt"]

            if len(cleaned) < 30 or not any(kw in cleaned.lower() for kw in ["follow", "growth", "network", "milestone"]):
                motif = random.choice(CREATIVE_VISUAL_MOTIFS)
                cleaned = f"Modern 3D conceptual art of {motif['name']}. {motif['description']} Crisp modern studio lighting, vibrant neon accents, dark slate background (#0A0E17)."

    # 4. Inject milestone badge if requested and not already present
    if include_milestone and str(milestone_num) not in cleaned:
        cleaned = f"{cleaned}, featuring an illuminated 3D milestone badge displaying '{milestone_num}' target counter"

    # 5. Mandatory strict anti-human and anti-cinematic reinforcement clause
    guard_clause = (
        ", modern 3D conceptual digital art, zero people, zero human faces or bodies, no realistic humans, "
        "no heavy cinematic drama, vibrant crisp modern studio rendering, high resolution 3D."
    )
    if not cleaned.endswith("."):
        cleaned = f"{cleaned.rstrip(',')}{guard_clause}"
    else:
        cleaned = f"{cleaned[:-1].rstrip(',')}{guard_clause}"

    return cleaned


class GrowthPostResult(BaseModel):
    tweet_copy: str = Field(..., description="High-converting creative growth/connection tweet copy with CTA")
    image_prompt: str = Field(..., description="Detailed AI creative image prompt with rich visual variation")
    aspect_ratio: str = Field(default="4:5", description="Creative image aspect ratio (4:5, 1:1, 16:9)")
    archetype: str = Field(..., description="Chosen growth archetype")
    cta_type: str = Field(default="open_question", description="Call-to-action type to drive comments")
    target_milestone: int | None = Field(default=None, description="Calculated next follower milestone")
    hashtags_count: int = Field(default=0, description="Exact number of hashtags in the tweet copy")
    language: str = Field(default="english", description="Language used for the post: english, hinglish, bilingual")
    visual_theme: str = Field(default="NEURAL_COMMUNITY_GRAPH", description="Visual theme motif identifier")
    length_tier: str = Field(default="compact", description="Chosen post length tier: ultra_punchy, compact, conversational")



async def generate_growth_post_spec(
    persona: Persona | None = None,
    current_followers: int = 0,
    preferred_archetype: str | None = None,
    target_hashtags: int | None = None,
    include_milestone: bool | None = None,
    language_mode: str | None = None,
    preferred_length_tier: str | None = None,
    client: Any | None = None,
) -> GrowthPostResult | None:
    """
    Synthesizes an authentic, high-converting creator post with a studio-grade 3D image prompt.
    Rooted in the persona's voice, worldview, and aesthetics.
    Strictly adheres to:
    1. Zero realistic humans (male/female/faces/bodies).
    2. Creative image referencing following & growth with diverse visual motifs & dynamic color palettes.
    3. Exactly 0, 1, or 2 hashtags randomly from growth pool (#F4F, #500Followers, #FollowForFollow, etc.).
    4. Autonomous X research data injection (CTAs, insights, sample hooks).
    5. Multi-language support: English, natural Romanized Hinglish, and Bilingual.
    6. Strict Gender Neutrality: NEVER admit, state, or imply male or female (neutral verbs and phrasing).
    7. Randomized Post Length: Varies across ultra-punchy micro, compact, and conversational lengths.
    """
    if client is None:
        client = get_ai_client()

    active_archetypes, archetype_prompts = get_active_archetypes()

    # 1. Determine Language Mode (hinglish, english, bilingual)
    if not language_mode or language_mode == "auto":
        # 45% Hinglish, 45% English, 10% Bilingual
        chosen_language = random.choices(["hinglish", "english", "bilingual"], weights=[0.45, 0.45, 0.10], k=1)[0]
    else:
        chosen_language = language_mode.lower().strip()
        if chosen_language not in GROWTH_LANGUAGES:
            chosen_language = "english"

    # 2. Determine Post Length Tier (randomized variation: 40% ultra_punchy, 40% compact, 20% conversational)
    if preferred_length_tier and preferred_length_tier in POST_LENGTH_TIERS:
        chosen_length_tier = preferred_length_tier
    else:
        chosen_length_tier = random.choices(["ultra_punchy", "compact", "conversational"], weights=[0.40, 0.40, 0.20], k=1)[0]
    length_spec = POST_LENGTH_TIERS[chosen_length_tier]

    if chosen_language == "hinglish":
        language_guidelines = (
            "LANGUAGE DIRECTIVE: HINGLISH (HINDI-ENGLISH MIX IN LATIN/ROMAN SCRIPT)\n"
            "- Write the tweet copy in natural, creator-friendly Hinglish (conversational mix of Hindi and English written strictly in the Latin alphabet).\n"
            "- STRICT CONSTRAINT: DO NOT use Devanagari script (NO हिंदी characters). Use English/Latin alphabet only, exactly how Indian creators, builders, and founders tweet on X and chat on WhatsApp.\n"
            "- STRICT GENDER NEUTRALITY: NEVER disclose, admit, or imply whether you are male or female. DO NOT use gendered verb inflections like 'chahti hoon' / 'chahta hoon', 'karungi' / 'karunga', 'rahi hoon' / 'raha hoon', 'sochti hoon' / 'sochta hoon'. Always use neutral phrasing like 'connect karna hai', 'connect karte hain', 'karna hai', 'lagta hai', 'sochte hain', 'drop karo'.\n"
            "- Tone: Energetic, authentic, relatable community builder. Zero cringe, zero robotic or spammy phrases.\n"
            "- Realistic Hinglish creator examples for inspiration:\n"
            "  * 'Feed pe inactive ghost followers collect karke kya fayda? Looking for active mutuals. Drop your handle below! 🤝'\n"
            "  * 'Chalo mutuals connect karte hain! Jo log actively build kar rahe hain, drop your @ below aur let us grow together 🚀'\n"
            "  * 'Timeline pe ghost followers se badhiya 100 genuine mutuals hain. Drop what you are working on right now 👇'\n"
            "  * 'Agla milestone hit karne se pehle want to connect with more builders. Drop a \"Hi\" below aur mutual bante hain! 🤝'"
        )
    elif chosen_language == "bilingual":
        language_guidelines = (
            "LANGUAGE DIRECTIVE: BILINGUAL (PUNCHY ENGLISH HOOK + HINGLISH CTA / PUNCHLINE)\n"
            "- Open with a strong, clean English hook, then transition into an authentic Hinglish call-to-action or observation in Roman/Latin script.\n"
            "- STRICT CONSTRAINT: DO NOT use Devanagari script. Use Roman/Latin script only.\n"
            "- STRICT GENDER NEUTRALITY: Keep all verbs and pronouns 100% gender-neutral. No 'chahti/chahta', no 'he/she', no 'guy/girl'.\n"
            "- Example:\n"
            "  * 'Vanity metrics mean nothing without real community. Seedha connect karte hain: drop your handle below and let us support each other! 🤝'"
        )
    else:
        language_guidelines = (
            "LANGUAGE DIRECTIVE: ENGLISH (GLOBAL CREATOR COMMUNITY)\n"
            "- Write in sharp, authentic modern creator English.\n"
            "- STRICT GENDER NEUTRALITY: Never state or imply whether you are male or female (no 'as a guy/girl/woman/man').\n"
            "- Conversational, human, high-signal community connection. No corporate or robotic phrasing."
        )

    # 3. Determine milestone and hashtag settings
    milestone_target = compute_next_milestone(current_followers)
    milestone_tag = f"#{milestone_target}Followers"

    if include_milestone is None:
        # ~45% probability to incorporate milestone badge in the visual
        include_milestone = random.random() < 0.45
    if target_hashtags is None:
        # Randomly 0, 1, or 2 hashtags
        target_hashtags = random.choice([0, 1, 2])

    # 4. Select Visual Theme & Dynamic Color Palette
    chosen_palette = random.choice(COLOR_PALETTES)
    primary_color, secondary_color = chosen_palette

    discovered_data = load_discovered_growth_ideas()
    discovered_concepts = discovered_data.get("discovered_image_concepts", [])

    motif_pool: list[dict[str, Any]] = list(CREATIVE_VISUAL_MOTIFS)
    if discovered_concepts and isinstance(discovered_concepts, list):
        for idx, concept in enumerate(discovered_concepts):
            if isinstance(concept, dict) and concept.get("title") and concept.get("prompt"):
                motif_pool.append({
                    "id": f"DISCOVERED_{idx + 1}",
                    "name": concept["title"],
                    "description": concept["prompt"],
                })

    chosen_motif = random.choice(motif_pool)
    visual_theme_id = chosen_motif.get("id", "NEURAL_COMMUNITY_GRAPH")
    visual_theme_name = chosen_motif.get("name", "Creator Community Constellation")
    visual_theme_desc = chosen_motif.get("description", "")

    # Aspect ratio: 80% 4:5 (vertical portrait for mobile screen dominance), 20% 1:1
    chosen_aspect_ratio = "4:5" if random.random() < 0.8 else "1:1"

    if include_milestone:
        dynamic_visual_directive = (
            f"Visual Theme: '{visual_theme_name}'. {visual_theme_desc}. "
            f"Prominently feature an illuminated 3D glassmorphic milestone badge or telemetry counter displaying target '{milestone_target}' (or 'Road to {milestone_target}'). "
            f"Color palette: glowing {primary_color} and {secondary_color} accents against sleek dark glassmorphism background (#0A0E17). "
            f"Clean modern 3D conceptual art, crisp studio lighting, zero humans, zero cinematic gloom."
        )
    else:
        dynamic_visual_directive = (
            f"Visual Theme: '{visual_theme_name}'. {visual_theme_desc}. "
            f"Focus on expanding network momentum, glowing mutual connections, and interactive digital elements. "
            f"Color palette: glowing {primary_color} and {secondary_color} accents against sleek dark glassmorphism background (#0A0E17). "
            f"Clean modern 3D conceptual art, crisp studio lighting, zero humans, zero cinematic gloom."
        )

    # 5. Dynamic Research Injection from Autonomous X Crawling
    research_section = ""
    high_converting_ctas = discovered_data.get("high_converting_ctas", [])
    key_insights = discovered_data.get("key_insights", [])
    sample_scraped = discovered_data.get("scraped_sample_posts", [])

    sampled_ctas = random.sample(high_converting_ctas, min(3, len(high_converting_ctas))) if high_converting_ctas else []
    sampled_insights = random.sample(key_insights, min(2, len(key_insights))) if key_insights else []
    sampled_hooks: list[str] = []
    if sample_scraped and isinstance(sample_scraped, list):
        for post in random.sample(sample_scraped, min(2, len(sample_scraped))):
            if isinstance(post, dict) and post.get("text"):
                first_line = post["text"].split("\n")[0].strip()
                if first_line:
                    sampled_hooks.append(first_line)

    if sampled_insights or sampled_ctas or sampled_hooks:
        research_lines = ["\n=== PROVEN HIGH-CONVERTING RESEARCH (From Bot's Live X Growth Analysis) ==="]
        if sampled_insights:
            research_lines.append("- Strategic Insights to apply:")
            for si in sampled_insights:
                research_lines.append(f"  * {si}")
        if sampled_ctas:
            research_lines.append("- Tested High-Converting CTAs for Inspiration (adapt naturally to your voice & language):")
            for cta in sampled_ctas:
                research_lines.append(f"  * \"{cta}\"")
        if sampled_hooks:
            research_lines.append("- Top Performing Real Hooks observed on X:")
            for hk in sampled_hooks:
                research_lines.append(f"  * \"{hk}\"")
        research_section = "\n".join(research_lines)

    # 6. Master Character Identity Anchor
    master_char_prompt = ""
    try:
        from xbot.persona.prompt_engine import build_character_master_prompt
        master_char_prompt = build_character_master_prompt(persona, action_type="growth")
    except Exception as e:
        logger.debug("Could not build master prompt for growth post: %s", e)

    if not master_char_prompt:
        creator_name = persona.display_name if persona else "Creator"
        creator_handle = f"@{persona.x_handle.lstrip('@')}" if persona and persona.x_handle else "@creator"
        master_char_prompt = f"You are {creator_name} ({creator_handle}), an authentic creator posting live on X (Twitter)."

    chosen_archetype = preferred_archetype if preferred_archetype in active_archetypes else random.choice(active_archetypes)
    archetype_directive = archetype_prompts.get(chosen_archetype, "Create an authentic high-signal creator post.")

    system_prompt = f"""{master_char_prompt}

=== TASK DIRECTIVE: HIGH-CONVERTING CREATIVE GROWTH POST WITH 3D VISUAL ===
You are creating an authentic, high-converting creator post paired with a unique 3D conceptual image prompt designed to attract active followers and mutuals to your profile on X (Twitter).

{language_guidelines}
{research_section}

STRICT GENDER NEUTRALITY DIRECTIVE (CRITICAL MANDATORY INVARIANT):
- NEVER disclose, state, or hint whether you are male or female in any post.
- NEVER say "as a guy/girl/man/woman/boy/female/male" or refer to yourself with gendered terms.
- NEVER use gendered labels or salutations like "bro", "bhai", "sis", "behen", "ladka", "ladki".
- IN HINGLISH / HINDI: NEVER use gender-specific verb inflections (e.g. FORBIDDEN: "chahti hoon", "chahta hoon", "karungi", "karunga", "rahi hoon", "raha hoon", "sochti hoon", "sochta hoon").
  Instead, ALWAYS use neutral/plural/infinitive constructions: "connect karna hai", "connect karte hain", "lagta hai", "sochte hain", "chalo connect karein", "milke grow karte hain".

POST LENGTH DIRECTIVE ({length_spec['name'].upper()}):
- Target Length: {length_spec['char_limit']}.
- Guideline: {length_spec['description']}
- It is NOT necessary to write a long post every time. Keep it strictly matching this length tier!
- If ultra_punchy: 1-2 short lines maximum! Hook + CTA directly, zero fluff.

CORE GROWTH & HASHTAG PRINCIPLES:
1. HIGH-ENERGY COMMUNITY GROWTH & MUTUALS CONNECTION:
   Post engaging, mutual-growth calls to connect with creators, builders, and peers on X.
   Make people excited to hit follow, connect as mutuals, and grow together.
2. CONVERSATIONAL CALL-TO-ACTION (CTA): End with a low-friction question or conversation trigger that real people want to jump in and answer.
3. HASHTAG RULE FOR THIS POST:
   - This post MUST have EXACTLY {target_hashtags} hashtag(s).
   - Recommended tags: #F4F, {milestone_tag}, #FollowForFollow, #FollowBack, #FollowTrain, #Mutuals.
   - If {target_hashtags} == 0: Do NOT include any hashtags in the tweet copy.
   - If {target_hashtags} == 1: Include exactly 1 growth hashtag (e.g. #F4F or {milestone_tag}).
   - If {target_hashtags} == 2: Include exactly 2 growth hashtags (e.g. #F4F {milestone_tag} or #FollowForFollow #Mutuals).
4. MOBILE WHITESPACE: Visual breathing room with double line breaks (\\n\\n).

IMAGE PROMPT DIRECTIVES (STRICT MANDATORY CONSTRAINTS):
1. ZERO REALISTIC HUMANS: NEVER include a realistic person, man, woman, human face, human skin, hands, or photorealistic human figures. The image MUST be modern 3D conceptual art, futuristic UI graphics, or abstract geometric growth constructs.
2. VISUAL THEME & MOTIF (MUST BE UNIQUE & NON-REPETITIVE):
   {dynamic_visual_directive}
3. NO HEAVY CINEMATIC DRAMA: Do NOT make a moody, dark, shadowy film-noir cinematic still. Keep the lighting clean, crisp, vibrant modern 3D studio lighting with sleek dark-mode glassmorphism (#0A0E17 backdrop, glowing accents).
4. Aspect ratio: '{chosen_aspect_ratio}' (vertical portrait for mobile screen dominance or square).

Return ONLY a JSON object matching this schema:
{{
  "tweet_copy": "Your complete high-converting post text in {chosen_language} (length: {length_spec['char_limit']}, sentence case, strictly gender-neutral, exactly {target_hashtags} hashtags)",
  "image_prompt": "Detailed 3D conceptual image prompt depicting '{visual_theme_name}' (zero humans, no heavy cinematic)",
  "aspect_ratio": "{chosen_aspect_ratio}",
  "archetype": "{chosen_archetype}",
  "cta_type": "open_question" | "vibe_check" | "debate_prompt" | "insight_share" | "mutuals_call"
}}
"""

    user_prompt = f"""Language: {chosen_language.upper()}
Post Length Tier: {length_spec['name']} ({length_spec['char_limit']})
Archetype: {chosen_archetype}
Archetype Focus: {archetype_directive}
Visual Theme: {visual_theme_name} ({visual_theme_id})
Colorway: {primary_color} + {secondary_color}
Current Followers: {current_followers}
Target Milestone: {milestone_target}
Milestone Featured in Visual: {"YES (feature target milestone " + str(milestone_target) + " badge/counter)" if include_milestone else "NO (focus on expanding community nodes & interactive elements)"}
Hashtag Target: {target_hashtags} hashtag(s) (use #F4F, {milestone_tag}, #FollowForFollow, etc.)

Generate a fresh, authentic creator post in {chosen_language} with length '{length_spec['name']}' ({length_spec['char_limit']}) and matching 3D growth visual prompt.
STRICT REQUIREMENTS:
1. NEVER reveal or admit whether you are male or female. Keep all verbs, pronouns, and phrasing 100% gender-neutral.
2. Adhere strictly to the chosen length tier: '{length_spec['name']}'. Do NOT write long posts when an ultra-punchy or compact length is chosen.
3. Ensure the visual unmistakably embodies '{visual_theme_name}' with ZERO humans and NO heavy cinematic slop.
"""

    model_cascade = getattr(
        settings, "MODEL_POST_CREATION", "litellm/gemini-flash-latest,litellm/deepseek-v4-flash-0731"
    )

    try:
        response = await client.chat.completions.create(
            model=model_cascade,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.8,
            max_tokens=1000,
        )

        content_str = response.choices[0].message.content or ""
        clean_json = content_str.strip()
        if "```" in clean_json:
            clean_json = re.sub(r"^```(?:json)?", "", clean_json, flags=re.MULTILINE)
            clean_json = re.sub(r"```$", "", clean_json, flags=re.MULTILINE).strip()

        start_idx = clean_json.find("{")
        end_idx = clean_json.rfind("}")
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            clean_json = clean_json[start_idx : end_idx + 1]

        data = None
        # 1. Try strict=False
        try:
            data = json.loads(clean_json, strict=False)
        except Exception:
            pass

        # 2. Try sanitizing unescaped newlines inside quotes
        if not data:
            try:
                sanitized = re.sub(r'(?<!\\)\n', r'\\n', clean_json)
                data = json.loads(sanitized, strict=False)
            except Exception:
                pass

        # 3. Robust regex fallback
        if not data or not isinstance(data, dict):
            tweet_match = re.search(r'"tweet_copy"\s*:\s*"((?:\\.|[^"\\])*?)(?:"|$)', clean_json, re.DOTALL)
            prompt_match = re.search(r'"image_prompt"\s*:\s*"((?:\\.|[^"\\])*?)(?:"|$)', clean_json, re.DOTALL)
            aspect_match = re.search(r'"aspect_ratio"\s*:\s*"([^"]+)"', clean_json)
            arch_match = re.search(r'"archetype"\s*:\s*"([^"]+)"', clean_json)
            cta_match = re.search(r'"cta_type"\s*:\s*"([^"]+)"', clean_json)

            data = {
                "tweet_copy": tweet_match.group(1).replace(r'\"', '"').replace(r'\n', '\n').strip() if tweet_match else "",
                "image_prompt": prompt_match.group(1).replace(r'\"', '"').replace(r'\n', '\n').strip() if prompt_match else "",
                "aspect_ratio": aspect_match.group(1).strip() if aspect_match else chosen_aspect_ratio,
                "archetype": arch_match.group(1).strip() if arch_match else chosen_archetype,
                "cta_type": cta_match.group(1).strip() if cta_match else "open_question",
            }

        tweet_text = strip_surrounding_quotes((data.get("tweet_copy") or "").strip())
        tweet_text = re.sub(r'^(?:\s*["\']?tweet_copy["\']?\s*:\s*["\']?)', '', tweet_text, flags=re.IGNORECASE).strip()
        tweet_text = strip_surrounding_quotes(tweet_text)

        image_p = strip_surrounding_quotes((data.get("image_prompt") or "").strip())
        image_p = re.sub(r'^(?:\s*["\']?image_prompt["\']?\s*:\s*["\']?)', '', image_p, flags=re.IGNORECASE).strip()
        image_p = strip_surrounding_quotes(image_p)
        ratio_val = (data.get("aspect_ratio") or chosen_aspect_ratio).strip()

        # Fallback if tweet_text is still empty
        if not tweet_text:
            clean_lines = []
            for l in clean_json.split("\n"):
                s = l.strip()
                if not s or s.startswith("{") or s.startswith("}"):
                    continue
                s = re.sub(r'^(?:\s*["\']?\w+["\']?\s*:\s*["\']?)', '', s)
                s = strip_surrounding_quotes(s)
                if s:
                    clean_lines.append(s)
            if clean_lines:
                tweet_text = "\n\n".join(clean_lines[:3])

        if not tweet_text:
            raise ValueError(f"No tweet_copy extracted from AI response (raw: {content_str[:150]})")

        # 6. Deterministic Post-Processing: Enforce gender neutrality (scrub any accidental gender admissions or verb inflections)
        clean_gender_text = sanitize_gender_neutrality(tweet_text)

        # 7. Deterministic Post-Processing: Enforce growth hashtag count (#F4F, #500Followers, etc.)
        final_tweet_copy = enforce_hashtag_count(
            text=clean_gender_text,
            target_count=target_hashtags,
            milestone_tag=milestone_tag,
        )

        # 8. Deterministic Post-Processing: Sanitize image prompt
        final_image_prompt = sanitize_growth_image_prompt(
            prompt=image_p,
            include_milestone=include_milestone,
            milestone_num=milestone_target,
            fallback_prompt=dynamic_visual_directive,
        )

        return GrowthPostResult(
            tweet_copy=final_tweet_copy,
            image_prompt=final_image_prompt,
            aspect_ratio=ratio_val or chosen_aspect_ratio,
            archetype=data.get("archetype", chosen_archetype),
            cta_type=data.get("cta_type", "open_question"),
            target_milestone=milestone_target if include_milestone else None,
            hashtags_count=target_hashtags,
            language=chosen_language,
            visual_theme=visual_theme_id,
            length_tier=chosen_length_tier,
        )
    except Exception as e:
        logger.error("Growth post AI generation failed: %s", e)
        return None


async def generate_growth_post_with_image(
    persona: Persona | None = None,
    current_followers: int = 0,
    output_dir: str | None = None,
    target_hashtags: int | None = None,
    include_milestone: bool | None = None,
    language_mode: str | None = None,
    preferred_length_tier: str | None = None,
    client: Any | None = None,
) -> tuple[GrowthPostResult | None, str | None]:
    """
    Generates growth copy and immediately renders a 3D conceptual growth image via ChatGPT (with Flux fallback).
    Returns (GrowthPostResult, local_image_file_path).
    """
    post_spec = await generate_growth_post_spec(
        persona=persona,
        current_followers=current_followers,
        target_hashtags=target_hashtags,
        include_milestone=include_milestone,
        language_mode=language_mode,
        preferred_length_tier=preferred_length_tier,
        client=client,
    )
    if not post_spec:
        return None, None

    ratio = getattr(post_spec, "aspect_ratio", "4:5") or "4:5"
    try:
        # provider_preference="auto" prioritizes ChatGPT Web Bridge (DALL-E 3)
        # and gracefully falls back to NVIDIA Flux if ChatGPT is busy or unavailable
        image_path = await generate_post_image_async(
            prompt=post_spec.image_prompt,
            aspect_ratio=ratio,
            output_dir=output_dir,
            provider_preference="auto",
        )
    except Exception as img_err:
        logger.warning("Growth image generation failed: %s", img_err)
        image_path = None

    return post_spec, image_path

