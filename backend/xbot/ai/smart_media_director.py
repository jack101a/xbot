"""
Smart Media Director: Context-Aware Visual Selection, Multimodal Vision Gate, and Auto-Cleanup.
"""

from __future__ import annotations

import asyncio
import hashlib
import io
import json
import logging
import os
from pathlib import Path
import random
import re
import time
from typing import Any

import httpx

from xbot.ai.client import get_ai_client
from xbot.ai.vision import _format_image_payload
from xbot.config import settings

logger = logging.getLogger(__name__)

SEARXNG_BASE_URL = getattr(settings, "SEARXNG_BASE_URL", "https://search.ajaxhs.duckdns.org")
WATERFALL_MEDIA_DIR = Path(settings.BASE_PROFILE_DIR).parent / "media" / "waterfall"
WATERFALL_MEDIA_DIR.mkdir(parents=True, exist_ok=True)

INTENT_SYSTEM_PROMPT = """You are the Lead Visual & Content Director for an elite social media account.
Your task is to analyze a drafted post and determine its optimal Visual Sourcing Strategy.

Choose exactly ONE of three visual intents:
1. "AUTHENTIC_STILL":
   - Use when the post discusses real-world facts, official studio news, confirmed cast/crew updates, official teasers, trailers, or event coverage.
   - Requires real, authentic photos/screenshots from verified X handles or studios.

2. "CREATIVE_AI_ART":
   - Use when the post discusses hypothetical scenarios, alternate universes (AU), lore "What-Ifs", imaginative concepts, or surreal questions where real photographs DO NOT EXIST in reality.
   - Example: "What if Harry was sorted into Slytherin?", "What if Harry used Avada Kedavra against Voldemort?", "Futuristic concept art".
   - You MUST provide a vivid, cinematic 4:5 vertical prompt for ChatGPT/DALL-E 3.

3. "TEXT_ONLY":
   - Use when the post is a punchy hot take, a sharp controversial question, a debate hook, or an interactive poll where adding an image would distract readers from the text, dilute discussion, or lower reply rate.

Return ONLY a valid JSON object matching this schema:
{
  "visual_intent": "AUTHENTIC_STILL" | "CREATIVE_AI_ART" | "TEXT_ONLY",
  "reasoning": "Brief explanation of why this visual strategy was chosen",
  "creative_image_prompt": "Cinematic 4:5 visual prompt if CREATIVE_AI_ART, else null",
  "expected_subject": "Description of what an authentic image must depict if AUTHENTIC_STILL, else null"
}
"""

VISION_GATE_PROMPT = """You are a strict Social Media Art Director.
Evaluate the provided image against the proposed post text.

Determine:
1. Does the image depict the actual topic, subject, or context mentioned in the post?
2. Is the visual quality high (clear, not broken, not an unrelated meme or selfie)?
3. Assign a relevance score from 1.0 to 10.0.

Rules:
- Score >= 7.5: Strongly relevant and enhances the post.
- Score < 7.5: Irrelevant, generic, or mismatched. Should be rejected.

Return ONLY a valid JSON object matching this schema:
{
  "matches_context": true | false,
  "relevance_score": float,
  "detected_subject": "Concise description of what is visible in the image",
  "verdict": "APPROVED" | "REJECTED",
  "reason": "Why it was approved or rejected"
}
"""


async def classify_post_visual_intent(post_text: str, campaign_topic: str) -> dict[str, Any]:
    """Classifies whether a post needs an authentic still, creative AI art, or pure text."""
    try:
        client = get_ai_client()
        user_prompt = f"Campaign Topic: {campaign_topic}\n\nDrafted Post:\n\"{post_text}\""

        response = await client.chat.completions.create(
            model="litellm/gemini-3.1-flash-lite",
            messages=[
                {"role": "system", "content": INTENT_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
            max_tokens=400,
        )
        raw = response.choices[0].message.content.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        return json.loads(raw)
    except Exception as e:
        logger.warning("classify_post_visual_intent failed: %s. Falling back to AUTHENTIC_STILL", e)
        return {
            "visual_intent": "AUTHENTIC_STILL",
            "reasoning": "Fallback on error",
            "creative_image_prompt": None,
            "expected_subject": None,
        }


async def verify_image_with_vision(image_path: str, post_text: str) -> dict[str, Any]:
    """Evaluates whether an image matches the post text with strict creator criteria."""
    try:
        client = get_ai_client()
        clean_url = _format_image_payload(image_path)

        user_content = [
            {
                "type": "text",
                "text": f"Post Text: \"{post_text}\"\n\nEvaluate whether this attached image matches the post.",
            },
            {
                "type": "image_url",
                "image_url": {"url": clean_url},
            },
        ]

        response = await client.chat.completions.create(
            model="litellm/gemini-3.1-flash-lite",
            messages=[
                {"role": "system", "content": VISION_GATE_PROMPT},
                {"role": "user", "content": user_content},
            ],
            temperature=0.1,
            max_tokens=300,
        )
        raw = response.choices[0].message.content.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        return json.loads(raw)
    except Exception as e:
        logger.warning("verify_image_with_vision failed on %s: %s", image_path, e)
        # Fail safe: reject if vision check errors
        return {
            "matches_context": False,
            "relevance_score": 0.0,
            "detected_subject": "Error during analysis",
            "verdict": "REJECTED",
            "reason": str(e),
        }


async def select_best_authentic_media(
    candidate_images: list[str],
    post_text: str,
    used_paths: set[str],
) -> str | None:
    """Inspects unused candidate images and returns the first one passing the Vision Gate."""
    for img_path in candidate_images:
        if not img_path or img_path in used_paths:
            continue
        if not os.path.exists(img_path):
            continue

        verdict = await verify_image_with_vision(img_path, post_text)
        if verdict.get("verdict") == "APPROVED" and verdict.get("relevance_score", 0.0) >= 7.5:
            logger.info("Vision Gate APPROVED image %s for post (Score: %.1f/10)", img_path, verdict.get("relevance_score"))
            return img_path
        else:
            logger.info("Vision Gate REJECTED image %s (Score: %.1f/10, Reason: %s)", img_path, verdict.get("relevance_score", 0), verdict.get("reason"))

    return None


def cleanup_expired_media(
    directories: list[Path] | None = None,
    max_age_hours: int = 48,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Deletes media files older than max_age_hours to prevent filling disk space."""
    if directories is None:
        directories = [
            Path("/home/ubuntu/projects/xbot/data/media"),
            Path(settings.BASE_PROFILE_DIR),
        ]

    now = time.time()
    cutoff_seconds = max_age_hours * 3600
    expired_files: list[Path] = []
    retained_files: list[Path] = []
    total_bytes_freed = 0

    for base_dir in directories:
        if not base_dir.exists():
            continue
        for root, _, files in os.walk(base_dir):
            for fname in files:
                ext = fname.lower().rsplit(".", 1)[-1] if "." in fname else ""
                if ext not in ("png", "jpg", "jpeg", "webp", "mp4"):
                    continue
                fpath = Path(root) / fname
                try:
                    stat = fpath.stat()
                    age_seconds = now - stat.st_mtime
                    if age_seconds > cutoff_seconds:
                        expired_files.append(fpath)
                        total_bytes_freed += stat.st_size
                        if not dry_run:
                            fpath.unlink()
                    else:
                        retained_files.append(fpath)
                except Exception as e:
                    logger.warning("Error inspecting %s for cleanup: %s", fpath, e)

    logger.info(
        "Media Cleanup (%s): Deleted %d files (>%dh), retained %d files, freed %.2f MB",
        "Dry-Run" if dry_run else "Live",
        len(expired_files),
        max_age_hours,
        len(retained_files),
        total_bytes_freed / (1024 * 1024),
    )
    return {
        "dry_run": dry_run,
        "max_age_hours": max_age_hours,
        "expired_count": len(expired_files),
        "retained_count": len(retained_files),
        "mb_freed": round(total_bytes_freed / (1024 * 1024), 2),
    }


# Blacklist of junk words / phrases for topics and hashtags
JUNK_TOPIC_REGEX = re.compile(
    r"(?i)\b(?:trending\s*(?:now|in\s+[\w\s]+)?|entertainment|news|sports|\d+[\d\.,]*\s*[kmb]?\s*posts?)\b|[·•|]",
    flags=re.IGNORECASE,
)

BLACK_LISTED_HASHTAGS = {
    "trending", "trendingnow", "trendingnowentertainment", "entertainment", "news",
    "trendingnownews", "posts", "post", "today", "viral", "update", "breaking",
    "daily", "thread", "explore", "timeline", "foryou", "fyp", "xyzbca",
    "video", "videos", "photo", "photos", "image", "images", "twitter", "x",
    "discussion", "share", "retweet", "follow"
}


def clean_topic_string(topic: str) -> str:
    """Removes X trend metadata (e.g. 'Trending now · Entertainment · 1K posts') leaving substantive topic."""
    if not topic:
        return ""
    cleaned = JUNK_TOPIC_REGEX.sub(" ", topic)
    cleaned = re.sub(r"[#\"'$$$$\(\)\[\]]+", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


CONTEXTUAL_METADATA_PROMPT = """You are an expert X (Twitter) social media editor.
Analyze this post and topic context to extract:
1. "search_entity": High-precision core subject entity for authentic image/photo search (e.g. '"SpaceX Starship" Flight 6', '"Ferrari" Monza F1 Charles Leclerc', '"GTA VI" Rockstar Games', '"iPhone Duo" Apple', '"The Batman" Matt Reeves'). Return the precise proper noun(s) with double quotes around key entities.
2. "media_hint": 2-3 words describing visual style (e.g. "photo press still", "gameplay screenshot", "cinematic still", "product design photo").
3. "hashtags": 1-2 authentic, contextual community hashtags on X for this topic (e.g. ['#SpaceX', '#Starship'], ['#Ferrari', '#F1'], ['#GTA6'], ['#Apple', '#iPhoneDuo'], ['#TheBatman', '#DC']).

Rules:
- NEVER use generic or junk tags (no #Trending, #News, #Entertainment, #Today, #Viral, #Post, #Explore, #Daily).
- Only choose 1 or 2 specific, authentic hashtags that match the exact subject of the post.
- If community candidates are relevant, prioritize authentic ones.

Return ONLY a valid JSON object matching this schema:
{
  "search_entity": "...",
  "media_hint": "...",
  "hashtags": ["#..."]
}"""


async def infer_contextual_metadata_ai(
    topic: str,
    post_text: str,
    candidate_hashtags: list[str] | None = None,
) -> dict[str, Any]:
    """
    Dynamically infers precision image search entity, visual style hint, and 1-2 authentic community hashtags
    using AI reasoning based on the exact post content and topic.
    Zero hardcoded brand, game, or franchise lists.
    """
    clean_top = clean_topic_string(topic)
    candidates_info = f"\nCommunity candidate tags: {', '.join(candidate_hashtags)}" if candidate_hashtags else ""
    user_prompt = f"Topic context: {clean_top}\nPost text: \"{post_text}\"{candidates_info}"

    try:
        client = get_ai_client()
        response = await asyncio.wait_for(
            client.chat.completions.create(
                model="litellm/gemini-3.1-flash-lite",
                messages=[
                    {"role": "system", "content": CONTEXTUAL_METADATA_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.2,
                max_tokens=150,
            ),
            timeout=8.0,
        )
        raw = response.choices[0].message.content.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        data = json.loads(raw)

        # Validate hashtags
        tags = data.get("hashtags", [])
        clean_tags = []
        seen = set()
        for t in tags:
            if not isinstance(t, str):
                continue
            t_clean = t.strip()
            if not t_clean.startswith("#"):
                t_clean = f"#{t_clean}"
            bare = t_clean.lower().replace("#", "")
            if bare not in BLACK_LISTED_HASHTAGS and len(bare) >= 2 and bare not in seen:
                seen.add(bare)
                clean_tags.append(t_clean)
        data["hashtags"] = clean_tags[:2]
        return data
    except Exception as e:
        logger.debug("infer_contextual_metadata_ai fallback: %s", e)
        return {}


def extract_precision_search_entity(topic: str, post_text: str = "") -> str:
    """
    Extracts high-precision core subject entity for image/GIF searches.
    Dynamic NLP extraction without any hardcoded franchise or brand lists.
    """
    clean_top = clean_topic_string(topic)
    combined = f"{clean_top}. {post_text}".strip()

    # 1. Multi-word capitalized proper noun phrases (e.g. "Rockstar Games", "Charles Leclerc", "Starbase Team")
    proper_nouns = re.findall(r"\b[A-Z][a-zA-Z0-9]+(?:\s+[A-Z][a-zA-Z0-9]+)+\b", combined)
    valid_pn = [
        pn for pn in proper_nouns
        if pn.lower() not in {"the new", "we need", "as long", "just dont", "whether it", "trending now", "what if", "let me", "in this"}
        and len(pn) > 4
    ]

    # 2. Alphanumeric product/version identifiers (e.g. "GTA VI", "GTA 6", "iPhone 18", "PS5", "F1")
    versions = re.findall(r"\b(?:[A-Z][a-zA-Z]+(?:\s*(?:VI|IV|V|IX|X|\d+))|\b(?:F1|PS5|PS4|RTX\s*\d+))\b", combined, flags=re.IGNORECASE)

    if valid_pn:
        primary = valid_pn[0]
        secondary = [p for p in valid_pn[1:] if p.lower() not in primary.lower()]
        if secondary:
            return f'"{primary}" {secondary[0]}'
        if versions and versions[0].lower() not in primary.lower():
            return f'"{primary}" {versions[0]}'
        return f'"{primary}"'

    if clean_top and len(clean_top) > 3:
        words = clean_top.split()
        if len(words) <= 3:
            return f'"{clean_top}"'
        return f'"{words[0]} {words[1]}" {" ".join(words[2:])}'

    return '"Tech News"'


def infer_relevant_hashtags(
    topic: str,
    post_text: str = "",
    candidate_hashtags: list[str] | None = None,
) -> list[str]:
    """
    Infers 1-2 authentic, contextual hashtags from topic and post text.
    Prioritizes live candidate hashtags (from X research), then dynamic NLP proper nouns & alphanumeric tags.
    Zero hardcoded domain lists. Never produces metadata junk like #TrendingNowEntertainment.
    """
    valid_tags: list[str] = []
    seen: set[str] = set()

    # Priority 1: Live candidate tags (scraped from X viral tweets or passed from AI)
    if candidate_hashtags:
        for ct in candidate_hashtags:
            if not isinstance(ct, str):
                continue
            c_clean = ct.strip()
            if not c_clean.startswith("#"):
                c_clean = f"#{c_clean}"
            bare = c_clean.lower().replace("#", "")
            if bare not in BLACK_LISTED_HASHTAGS and len(bare) >= 2 and bare not in seen:
                seen.add(bare)
                valid_tags.append(c_clean)

    # Priority 2: Dynamic NLP extraction from topic and post text
    if not valid_tags:
        clean_top = clean_topic_string(topic)
        combined = f"{clean_top}. {post_text}".strip()

        # Extract alphanumeric version tags (e.g. "GTA6", "iPhone18", "PS5", "F1")
        alphanumeric = re.findall(r"\b([A-Za-z]+(?:\d+|[IVXLCDM]+))\b", combined)
        for an in alphanumeric:
            bare = an.lower()
            if bare not in BLACK_LISTED_HASHTAGS and len(bare) >= 2 and bare not in seen:
                seen.add(bare)
                valid_tags.append(f"#{an}")

        # Extract capitalized multi-word phrases as CamelCase tags
        proper_nouns = re.findall(r"\b[A-Z][a-zA-Z0-9]+(?:\s+[A-Z][a-zA-Z0-9]+)+\b", combined)
        for pn in proper_nouns:
            if pn.lower() in {"the new", "we need", "as long", "just dont", "whether it", "trending now", "what if"}:
                continue
            words = [w for w in pn.split() if w.isalnum()]
            if words:
                tag = "#" + "".join(w.capitalize() for w in words)
                bare = tag.lower().replace("#", "")
                if bare not in BLACK_LISTED_HASHTAGS and len(bare) >= 3 and bare not in seen:
                    seen.add(bare)
                    valid_tags.append(tag)

        # Single prominent capital words from topic
        for tw in clean_top.split():
            if tw.isupper() or (tw.istitle() and len(tw) >= 4):
                bare = tw.lower()
                if bare not in BLACK_LISTED_HASHTAGS and bare not in seen:
                    seen.add(bare)
                    valid_tags.append(f"#{tw.capitalize()}")

    if not valid_tags:
        return []

    # Pick 1 or 2 tags with natural variance
    if len(valid_tags) == 1:
        return valid_tags

    # 75% chance of 2 hashtags, 25% chance of 1 hashtag
    sample_size = 2 if random.random() < 0.75 else 1
    return random.sample(valid_tags, min(len(valid_tags), sample_size))


def ensure_main_post_hashtags(
    post_text: str,
    topic: str = "",
    candidate_hashtags: list[str] | None = None,
) -> str:
    """
    Guarantees that a main post (standalone post, thread hook/closer, trend take)
    contains 1-2 authentic hashtags for algorithmic search indexing.
    Strips any metadata junk hashtags (e.g. #TrendingNowEntertainment).
    Does NOT affect replies (which enforce 0 hashtags).
    """
    if not post_text:
        return post_text

    # Extract existing hashtags
    existing_tags = re.findall(r"#\w+", post_text)
    junk_found = [t for t in existing_tags if t.lower().replace("#", "") in BLACK_LISTED_HASHTAGS or "trending" in t.lower()]

    clean_post = post_text
    if junk_found:
        for jt in junk_found:
            clean_post = clean_post.replace(jt, "")
        clean_post = re.sub(r"  +", " ", clean_post).strip()
        existing_tags = [t for t in existing_tags if t not in junk_found]

    if len(existing_tags) >= 1:
        from xbot.ai.anti_ai_gatekeeper import AntiAIGatekeeper
        return AntiAIGatekeeper.enforce_max_hashtags(clean_post.strip(), max_tags=2)

    tags = infer_relevant_hashtags(topic, clean_post, candidate_hashtags=candidate_hashtags)
    if not tags:
        clean_top = clean_topic_string(topic)
        t_slug = re.sub(r"[^\w]+", "", clean_top)[:15]
        if t_slug and t_slug.lower() not in BLACK_LISTED_HASHTAGS:
            tags = [f"#{t_slug.capitalize()}"]

    if not tags:
        return clean_post.strip()

    tag_str = " ".join(tags)
    if len(clean_post) + len(tag_str) + 2 <= 280:
        return f"{clean_post.rstrip()}\n\n{tag_str}"

    sorted_tags = sorted(tags, key=len)
    if len(clean_post) + len(sorted_tags[0]) + 2 <= 280:
        return f"{clean_post.rstrip()}\n\n{sorted_tags[0]}"

    # If post is already near 280 limit, only trim if there is a natural sentence boundary
    avail = 280 - len(sorted_tags[0]) - 5
    cutoff = clean_post[:avail].rfind(". ")
    if cutoff > 140:
        return f"{clean_post[:cutoff + 1].rstrip()}\n\n{sorted_tags[0]}"

    # Preserve complete tweet rather than mangling it with ellipsis
    return clean_post.strip()


async def search_searxng_precision(
    topic: str,
    post_text: str = "",
    media_hint: str = "",
    max_candidates: int = 4,
    precision_entity: str | None = None,
) -> list[dict[str, Any]]:
    """
    SearXNG Precision Mode:
    Queries Google Images and Bing Images with negative filters (-icon -logo -vector -clipart -stock)
    and extracts high-resolution candidate photos (>= 800px width).
    """
    entity_query = precision_entity or extract_precision_search_entity(topic, post_text)

    hint = media_hint.strip() if media_hint else ""
    if not hint:
        combined = f"{topic} {post_text}".lower()
        if any(k in combined for k in ("game", "gaming", "playstation", "xbox", "nintendo", "steam")):
            hint = "screenshot wallpaper"
        elif any(k in combined for k in ("hardware", "phone", "tech", "laptop", "device")):
            hint = "product design photo"
        elif any(k in combined for k in ("movie", "film", "cinema", "actor", "series", "trailer")):
            hint = "movie still"
        else:
            hint = "photo press still"

    query = f'!bing_images !google_images {entity_query} {hint} -icon -logo -vector -clipart -stock -avatar -drawing'
    logger.info("SearXNG Precision query: %s", query)

    candidates: list[dict[str, Any]] = []
    params = {
        "q": query,
        "format": "json",
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(f"{SEARXNG_BASE_URL}/search", params=params)
            if resp.status_code == 200:
                data = resp.json()
                results = data.get("results", [])
                for r in results:
                    img_src = r.get("img_src") or ""
                    res = r.get("resolution") or ""
                    title = r.get("title") or ""

                    if not img_src or img_src.lower().endswith(".svg") or "icon" in img_src.lower():
                        continue
                    if any(k in title.lower() for k in ("icon", "logo", "clipart", "vector", "drawing")):
                        continue

                    width = 0
                    if res and ("x" in res.lower() or "×" in res):
                        parts = re.split(r"[x×]", res.lower())
                        try:
                            width = int(parts[0].strip())
                        except ValueError:
                            pass

                    candidates.append({
                        "source": f"SearXNG_{r.get('engine', 'web')}",
                        "url": img_src,
                        "resolution": res or "High-Res",
                        "title": title[:80],
                        "width": width,
                    })
                    if len(candidates) >= max_candidates:
                        break
    except Exception as e:
        logger.warning("SearXNG Precision search failed: %s", e)

    logger.info("SearXNG Precision returned %d candidate(s) for '%s'", len(candidates), entity_query)
    return candidates


async def download_and_verify_image(
    candidate_url: str,
    output_path: Path,
    min_width: int = 600,
    min_height: int = 400,
) -> str | None:
    """Downloads an image URL and validates that it is a genuine, high-resolution photo."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
    }
    try:
        async with httpx.AsyncClient(timeout=18.0, follow_redirects=True) as client:
            resp = await client.get(candidate_url, headers=headers)
            content_type = resp.headers.get("content-type", "").lower()
            if "image" not in content_type and "octet-stream" not in content_type:
                logger.debug("Candidate %s rejected: non-image content-type '%s'", candidate_url, content_type)
                return None

            if resp.status_code == 200 and len(resp.content) >= 15000:
                try:
                    from PIL import Image
                    with Image.open(io.BytesIO(resp.content)) as im:
                        w, h = im.size
                        if w < min_width or h < min_height:
                            logger.info("Candidate image rejected: dimensions %dx%d below %dx%d threshold", w, h, min_width, min_height)
                            return None
                        ext = output_path.suffix.lower()
                        if ext in (".jpg", ".jpeg") and im.mode in ("RGBA", "P"):
                            im = im.convert("RGB")
                        im.save(output_path, quality=92)
                except Exception as pil_err:
                    logger.debug("Pillow verification failed on %s: %s", candidate_url, pil_err)
                    return None

                logger.info("Successfully downloaded and verified %s (size: %d KB)", output_path.name, len(resp.content) // 1024)
                return str(output_path)
            else:
                logger.debug("Image download invalid: status %s, size %d bytes", resp.status_code, len(resp.content))
    except Exception as ex:
        logger.debug("download_and_verify_image failed for %s: %s", candidate_url, ex)
    return None


async def resolve_post_media_waterfall(
    topic: str,
    post_text: str,
    profile_slug: str = "test_profile1",
    media_hint: str = "",
    candidate_images: list[str] | None = None,
    candidate_hashtags: list[str] | None = None,
    allow_gif: bool = True,
    used_media_paths: set[str] | None = None,
) -> tuple[list[str], str | None, str]:
    """
    Executes the strict Media Sourcing Waterfall:
    1. Priority 1: X Sourcing (Authentic media from scraped X tweets/outlets).
    2. Priority 2: SearXNG Precision Mode (Bing/Google Images studio/press photos with negative filters & resolution gate).
    3. Priority 3: Dynamic Reaction GIF query (Tenor via Playwright composer) or Canvas fallback.

    Also enforces that the main post text includes 1-2 relevant hashtags.

    Returns:
        (media_paths, gif_query, enriched_post_text)
    """
    if used_media_paths is None:
        used_media_paths = set()

    # Dynamic AI inference for precision entity, visual hint, and contextual hashtags
    ai_meta = await infer_contextual_metadata_ai(topic, post_text, candidate_hashtags=candidate_hashtags)
    inferred_tags = ai_meta.get("hashtags") or candidate_hashtags
    enriched_text = ensure_main_post_hashtags(post_text, topic, candidate_hashtags=inferred_tags)

    inferred_entity = ai_meta.get("search_entity") or extract_precision_search_entity(topic, enriched_text)
    inferred_hint = media_hint or ai_meta.get("media_hint") or ""

    entity_str = inferred_entity.replace('"', '')
    slug = re.sub(r"[^\w]+", "_", entity_str.lower()).strip("_")[:25] or "post"

    # Priority 1: Authentic X Media (from scraped tweets / existing pool)
    if candidate_images:
        logger.info("[Media Waterfall Tier 1] Checking %d authentic candidate images for '%s'", len(candidate_images), topic[:30])
        best_x_img = await select_best_authentic_media(candidate_images, enriched_text, used_media_paths)
        if best_x_img:
            logger.info("[Media Waterfall Tier 1 WINNER] Approved authentic X image: %s", best_x_img)
            used_media_paths.add(best_x_img)
            return [best_x_img], None, enriched_text

    # Priority 2: SearXNG Precision Mode (Bing/Google Images)
    logger.info("[Media Waterfall Tier 2] Initiating SearXNG Precision Mode for '%s'...", topic[:30])
    searx_candidates = await search_searxng_precision(
        topic,
        post_text=enriched_text,
        media_hint=inferred_hint,
        max_candidates=3,
        precision_entity=inferred_entity,
    )
    for idx, cand in enumerate(searx_candidates):
        cand_url = cand.get("url")
        if not cand_url or cand_url in used_media_paths:
            continue
        ext = ".png" if ".png" in cand_url.lower() else ".jpg"
        target_file = WATERFALL_MEDIA_DIR / f"{slug}_searx_{idx}{ext}"
        saved = await download_and_verify_image(cand_url, target_file, min_width=600, min_height=400)
        if saved and os.path.exists(saved):
            verdict = await verify_image_with_vision(saved, enriched_text)
            if verdict.get("verdict") == "APPROVED" or verdict.get("relevance_score", 0.0) >= 6.8:
                logger.info("[Media Waterfall Tier 2 WINNER] SearXNG Precision image approved: %s (Score: %.1f)", saved, verdict.get("relevance_score", 0.0))
                used_media_paths.add(saved)
                return [saved], None, enriched_text
            else:
                logger.info("Vision Gate rejected candidate %s (Score: %.1f, Reason: %s)", saved, verdict.get("relevance_score", 0.0), verdict.get("reason"))

    # Priority 3: Reaction GIF / Dynamic Tenor Fallback
    if allow_gif:
        clean_gif_query = re.sub(r'["\']', '', inferred_entity)
        clean_gif_query = re.sub(r'\b(?:movie still|studio photo|photo press still|cinematic still|product design photo|gameplay screenshot)\b', '', clean_gif_query, flags=re.IGNORECASE).strip()
        clean_gif_query = re.sub(r'\s+', ' ', clean_gif_query)

        # Check if gif query is meaningful and not generic/junk
        is_junk = (
            not clean_gif_query
            or len(clean_gif_query) < 3
            or clean_gif_query.lower() in {
                "tech news", "trending", "trending now", "entertainment", "news",
                "posts", "photo press still", "concept design photo", "screenshot wallpaper"
            }
            or any(j in clean_gif_query.lower() for j in ("trending", "posts", "entertainment"))
        )
        if not is_junk:
            logger.info("[Media Waterfall Tier 3 WINNER] Fallback to authentic Reaction GIF query: '%s'", clean_gif_query)
            return [], clean_gif_query, enriched_text
        else:
            logger.info("[Media Waterfall Tier 3] Generic/junk GIF query ('%s') rejected to preserve post quality.", clean_gif_query)

    return [], None, enriched_text

