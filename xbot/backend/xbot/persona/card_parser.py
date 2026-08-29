import json
import logging
from pathlib import Path
from typing import Any, Dict

from ruamel.yaml import YAML

logger = logging.getLogger(__name__)
yaml = YAML(typ="safe")
yaml.default_flow_style = False


def load_raw_card(content_or_path: str) -> Dict[str, Any]:
    """
    Loads a character card from either an absolute file path on the server or raw JSON/YAML string.
    Returns a dictionary.
    """
    content_or_path = content_or_path.strip()
    
    # Check if it looks like a file path
    if (content_or_path.startswith("/") or content_or_path.startswith("C:\\")) and len(content_or_path) < 500:
        file_path = Path(content_or_path)
        if file_path.exists() and file_path.is_file():
            logger.info(f"Loading character card from file path: {file_path}")
            with file_path.open("r", encoding="utf-8") as f:
                if file_path.suffix.lower() in [".yaml", ".yml"]:
                    return yaml.load(f) or {}
                else:
                    return json.load(f) or {}

    # Try parsing as JSON first
    try:
        return json.loads(content_or_path)
    except Exception:
        pass

    # Try parsing as YAML
    try:
        data = yaml.load(content_or_path)
        if isinstance(data, dict):
            return data
    except Exception:
        pass

    # If all fail, treat as raw text description
    return {"raw_text": content_or_path}


def map_card_to_persona(card: Dict[str, Any], existing_id: str = "custom-persona", existing_slug: str = "bot") -> Dict[str, Any]:
    """
    Deterministically maps any structured character card (such as Kaya's JSON schema, TavernAI, or Character.AI)
    into our standard 7-Dimension Bedrock Persona format without losing any data.
    """
    if "raw_text" in card and len(card) == 1:
        # Simple text input fallback
        text = card["raw_text"]
        return {
            "id": existing_id,
            "display_name": existing_slug.capitalize(),
            "x_handle": existing_slug.lower(),
            "identity": {
                "age": 25,
                "location": "Global",
                "occupation": "Digital Personality",
                "education": "Self-taught / Evolving AI",
                "background": text[:500]
            },
            "personality": {
                "traits": ["Expressive", "Engaging", "Authentic"],
                "values": ["Consistency", "Value Creation"],
                "communication_style": "Natural and contextual"
            },
            "writing_style": {
                "tone": "Conversational",
                "typical_length": "Short and punchy",
                "formatting": ["No emojis unless appropriate", "Clean spacing"],
                "examples": []
            },
            "goals": {
                "short_term": ["Build authentic connection with audience"],
                "long_term": ["Establish recognizable brand identity"],
                "content_pillars": ["Daily insights", "Interactive discussions"]
            },
            "rules": {
                "always": ["Stay in character", "Provide engaging replies"],
                "never": ["Break character", "Engage in hate speech or spam"]
            },
            "interests": {
                "primary": ["Technology", "Culture", "Lifestyle"],
                "secondary": ["Art", "Trends"],
                "will_not_discuss": ["Controversial politics", "Spam"]
            },
            "system_prompt": text,
            "tone_prompt": "Conversational and natural",
            "raw_character_card": card
        }

    # Extract name and handles
    name = (
        card.get("character_identity", {}).get("name") or 
        card.get("name") or 
        card.get("char_name") or 
        card.get("display_name") or 
        existing_slug.capitalize()
    )
    display_name = card.get("social_media_identity", {}).get("display_name") or name
    x_handle = (
        card.get("social_media_identity", {}).get("instagram_username", "")
        or card.get("social_media_identity", {}).get("x_handle", "")
        or card.get("x_handle", "")
        or f"@{name.lower().replace(' ', '')}"
    ).replace("@", "").replace(".ai", "")

    # 1. Identity
    char_id = card.get("character_identity", {})
    bg_parts = [
        char_id.get("core_summary", ""),
        card.get("final_character_summary", ""),
        card.get("description", ""),
        card.get("personality", "") if isinstance(card.get("personality"), str) else "",
        f"Role: {char_id.get('public_role', '')}" if char_id.get("public_role") else "",
        f"Education: {card.get('education', {}).get('degree', '')} from {card.get('education', {}).get('university', '')}" if card.get("education") else ""
    ]
    background = "\n\n".join([p for p in bg_parts if p]).strip() or "Autonomous AI creator and social media personality."

    # 2. Personality
    pers = card.get("personality", {})
    if isinstance(pers, dict):
        traits = pers.get("public_persona", []) + pers.get("private_persona", []) + pers.get("core_traits", [])
        humor = pers.get("humor_style", "")
        comm_style = f"Humor & style: {humor}." if humor else "Confident, expressive, and audience-aware."
    else:
        traits = [t.strip() for t in str(pers).split(",") if t.strip()] if pers else ["Confident", "Authentic"]
        comm_style = "Expressive and engaging."

    if not traits:
        traits = ["Confident", "Expressive", "Strategic", "Warm", "Trend-aware"]

    values = (
        card.get("dreams_and_motivation", {}).get("long_term_goals", []) or 
        card.get("values", []) or 
        ["Authenticity", "Audience Growth", "Consistent Quality"]
    )

    # 3. Writing Style
    cap = card.get("caption_style", {}) if isinstance(card.get("caption_style"), dict) else {}
    tone_rules = cap.get("rules", []) or card.get("writing_style", {}).get("tone", "playful, self-aware, and concise")
    tone = ", ".join(tone_rules) if isinstance(tone_rules, list) else str(tone_rules)
    typical_len = card.get("writing_style", {}).get("typical_length", "short, punchy, caption-friendly")
    formatting = cap.get("rules", []) if isinstance(cap.get("rules"), list) else ["No unnecessary hashtags", "Keep spacing clean"]
    examples = cap.get("examples", []) or card.get("mes_example", "").split("\n") or []
    examples = [ex for ex in examples if ex and isinstance(ex, str)]

    # 4. Rules
    always = (
        card.get("do_not_change", []) + 
        card.get("image_generation_rules", {}).get("important_visual_rules", []) +
        card.get("rules", {}).get("always", [])
    )
    if not always:
        always = ["Maintain consistent personality", "Be responsive and engaging"]

    never = (
        card.get("dislikes", {}).get("personal_dislikes", []) + 
        card.get("dislikes", {}).get("content_dislikes", []) + 
        card.get("body_confidence_and_sensuality", {}).get("boundaries", []) +
        card.get("rules", {}).get("never", [])
    )
    if not never:
        never = ["Break character", "Generate spam or generic corporate text"]

    # 5. Interests
    likes = card.get("likes", {}) if isinstance(card.get("likes"), dict) else {}
    raw_pillars = card.get("social_media_identity", {}).get("content_pillars", {})
    if isinstance(raw_pillars, dict):
        content_pillars = list(raw_pillars.values())
    elif isinstance(raw_pillars, list):
        content_pillars = raw_pillars
    else:
        content_pillars = []
    primary_interests = likes.get("daily_likes", []) + content_pillars + card.get("interests", {}).get("primary", [])
    if not primary_interests:
        primary_interests = ["Lifestyle", "Tech", "Culture", "Fashion", "Daily thoughts"]

    secondary_interests = (
        likes.get("creative_likes", []) + 
        card.get("interests", {}).get("books_and_nerdy_interests", {}).get("genres", []) +
        card.get("interests", {}).get("secondary", [])
    )
    if not secondary_interests:
        secondary_interests = ["Emerging trends", "Creative design", "Music", "Cinema"]

    will_not_discuss = (
        card.get("fears", []) + 
        card.get("dislikes", {}).get("content_dislikes", []) +
        card.get("interests", {}).get("will_not_discuss", [])
    )
    if not will_not_discuss:
        will_not_discuss = ["Controversial politics", "Spam", "Unverified financial advice"]

    # System prompt anchor
    sys_prompt = card.get("final_character_summary") or card.get("core_summary") or background

    persona_dict = {
        "id": existing_id,
        "display_name": display_name,
        "x_handle": x_handle,
        "identity": {
            "age": char_id.get("age", 25) if isinstance(char_id, dict) else 25,
            "location": char_id.get("city", "Delhi") if isinstance(char_id, dict) and "city" in char_id else "Global",
            "occupation": char_id.get("public_role", "AI Creator") if isinstance(char_id, dict) else "AI Creator",
            "education": card.get("education", {}).get("degree", "Self-taught") if isinstance(card.get("education"), dict) else "Self-taught",
            "background": background
        },
        "personality": {
            "traits": traits[:15],
            "values": values[:10],
            "communication_style": comm_style
        },
        "writing_style": {
            "tone": tone,
            "typical_length": typical_len,
            "formatting": formatting[:10],
            "examples": examples[:10]
        },
        "goals": {
            "short_term": [card.get("dreams_and_motivation", {}).get("short_term_goal", "Establish recognizable daily presence")] if isinstance(card.get("dreams_and_motivation"), dict) else ["Grow daily audience"],
            "long_term": values[:10],
            "content_pillars": list(card.get("social_media_identity", {}).get("content_pillars", {}).values())[:10] if isinstance(card.get("social_media_identity", {}).get("content_pillars"), dict) else ["Lifestyle", "Tech", "Daily reflections"]
        },
        "rules": {
            "always": always[:15],
            "never": never[:15]
        },
        "interests": {
            "primary": primary_interests[:15],
            "secondary": secondary_interests[:15],
            "will_not_discuss": will_not_discuss[:15]
        },
        "system_prompt": sys_prompt,
        "tone_prompt": tone,
        "raw_character_card": card
    }

    return persona_dict
