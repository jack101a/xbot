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
        for kw in ["follow", "growth", "network", "milestone", "connection", "nodes", "community", "trajectory", "momentum"]
    )

    if len(cleaned) < 30 or not has_growth_keywords:
        # Check if we have discovered image concepts from X research
        discovered = load_discovered_growth_ideas()
        concepts = discovered.get("discovered_image_concepts", [])
        if concepts and isinstance(concepts, list):
            chosen_c = random.choice(concepts)
            if isinstance(chosen_c, dict) and chosen_c.get("prompt"):
                cleaned = chosen_c["prompt"]

        if len(cleaned) < 30 or not any(kw in cleaned.lower() for kw in ["follow", "growth", "network", "milestone"]):
            if include_milestone:
                cleaned = (
                    f"Modern 3D conceptual art of a glowing glassmorphic milestone badge displaying '{milestone_num}' target counter, "
                    "surrounded by expanding interconnected glowing creator network nodes and an ascending glowing trajectory curve. "
                    "Crisp studio lighting, vibrant neon cyan and amber accents, dark slate background (#0A0E17)."
                )
            else:
                cleaned = (
                    "Modern 3D conceptual art featuring a sleek floating glowing 'Follow' interaction pill button radiating electric cyan and violet light, "
                    "connected via glowing digital data streams to interconnected community nodes and an ascending growth velocity curve. "
                    "Clean isometric perspective, crisp modern studio lighting, dark minimalist background (#0A0E17)."
                )

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


async def generate_growth_post_spec(
    persona: Persona | None = None,
    current_followers: int = 0,
    preferred_archetype: str | None = None,
    target_hashtags: int | None = None,
    include_milestone: bool | None = None,
    client: Any | None = None,
) -> GrowthPostResult | None:
    """
    Synthesizes an authentic, high-converting creator post with a studio-grade 3D image prompt.
    Rooted in the persona's voice, worldview, and aesthetics.
    Strictly adheres to:
    1. Zero realistic humans (male/female/faces/bodies).
    2. Creative image referencing following & growth (no heavy cinematic drama).
    3. Exactly 0, 1, or 2 hashtags randomly from growth pool (#F4F, #500Followers, #FollowForFollow, etc.).
    4. Dynamically refreshed with ideas from X search research.
    """
    if client is None:
        client = get_ai_client()

    active_archetypes, archetype_prompts = get_active_archetypes()

    # 1. Determine milestone and hashtag settings
    milestone_target = compute_next_milestone(current_followers)
    milestone_tag = f"#{milestone_target}Followers"

    if include_milestone is None:
        # ~45% probability to incorporate milestone badge in the visual
        include_milestone = random.random() < 0.45
    if target_hashtags is None:
        # Randomly 0, 1, or 2 hashtags
        target_hashtags = random.choice([0, 1, 2])

    # 2. Master Character Identity Anchor
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

    milestone_visual_directive = (
        f"Feature a prominent 3D glowing milestone badge or progress card displaying the target '{milestone_target}' or 'Road to {milestone_target}', "
        f"surrounded by glowing interconnected follower network nodes and an upward trajectory curve."
        if include_milestone
        else "Feature a prominent 3D glowing 'Follow' interaction pill button radiating electric cyan and violet light, surrounded by expanding interconnected creator network nodes and ascending momentum."
    )

    system_prompt = f"""{master_char_prompt}

=== TASK DIRECTIVE: HIGH-CONVERTING CREATIVE GROWTH POST WITH 3D VISUAL ===
You are creating an authentic, high-converting creator post paired with a 3D conceptual image prompt designed to attract active followers to your profile on X (Twitter).

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
2. VISUAL THEME: FOLLOWING FOR GROWTH & NETWORK EXPANSION:
   The visual must INSTANTLY signal to anyone scrolling that this is about FOLLOWING FOR GROWTH, COMMUNITY, and NETWORKING.
   Directive: {milestone_visual_directive}
3. NO HEAVY CINEMATIC DRAMA: Do NOT make a moody, dark, shadowy film-noir cinematic still. Keep the lighting clean, crisp, vibrant modern 3D studio lighting with sleek dark-mode glassmorphism (#0A0E17 backdrop, electric cyan, violet, or golden amber glow).
4. Aspect ratio: '4:5' (vertical portrait for mobile screen dominance) or '1:1'.

Return ONLY a JSON object matching this schema:
{{
  "tweet_copy": "Your complete high-converting post text (natural length, sentence case, exactly {target_hashtags} hashtags)",
  "image_prompt": "Detailed 3D conceptual image prompt depicting following for growth (zero humans, no heavy cinematic)",
  "aspect_ratio": "4:5",
  "archetype": "{chosen_archetype}",
  "cta_type": "open_question" | "vibe_check" | "debate_prompt" | "insight_share" | "mutuals_call"
}}
"""

    user_prompt = f"""Archetype: {chosen_archetype}
Archetype Focus: {archetype_directive}
Current Followers: {current_followers}
Target Milestone: {milestone_target}
Milestone Featured in Visual: {"YES (feature target milestone " + str(milestone_target) + " badge/card)" if include_milestone else "NO (focus on glowing 3D Follow button and expanding creator network nodes)"}
Hashtag Target: {target_hashtags} hashtag(s) (use #F4F, {milestone_tag}, #FollowForFollow, etc.)

Generate a fresh, authentic creator post and matching 3D growth visual prompt in your voice.
Ensure the visual unmistakably signals following for growth with ZERO humans and NO heavy cinematic slop.
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
                "aspect_ratio": aspect_match.group(1).strip() if aspect_match else "4:5",
                "archetype": arch_match.group(1).strip() if arch_match else chosen_archetype,
                "cta_type": cta_match.group(1).strip() if cta_match else "open_question",
            }

        tweet_text = strip_surrounding_quotes((data.get("tweet_copy") or "").strip())
        tweet_text = re.sub(r'^(?:\s*["\']?tweet_copy["\']?\s*:\s*["\']?)', '', tweet_text, flags=re.IGNORECASE).strip()
        tweet_text = strip_surrounding_quotes(tweet_text)

        image_p = strip_surrounding_quotes((data.get("image_prompt") or "").strip())
        image_p = re.sub(r'^(?:\s*["\']?image_prompt["\']?\s*:\s*["\']?)', '', image_p, flags=re.IGNORECASE).strip()
        image_p = strip_surrounding_quotes(image_p)
        ratio_val = (data.get("aspect_ratio") or "4:5").strip()

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

        # 4. Deterministic Post-Processing: Enforce growth hashtag count (#F4F, #500Followers, etc.)
        final_tweet_copy = enforce_hashtag_count(
            text=tweet_text,
            target_count=target_hashtags,
            milestone_tag=milestone_tag,
        )

        # 5. Deterministic Post-Processing: Sanitize image prompt
        final_image_prompt = sanitize_growth_image_prompt(
            prompt=image_p,
            include_milestone=include_milestone,
            milestone_num=milestone_target,
        )

        return GrowthPostResult(
            tweet_copy=final_tweet_copy,
            image_prompt=final_image_prompt,
            aspect_ratio=ratio_val,
            archetype=data.get("archetype", chosen_archetype),
            cta_type=data.get("cta_type", "open_question"),
            target_milestone=milestone_target if include_milestone else None,
            hashtags_count=target_hashtags,
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
