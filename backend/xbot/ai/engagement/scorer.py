from __future__ import annotations

from typing import Any
from xbot.persona import LearnedState, Persona, Relationships, build_worldview_prompt_section
from xbot.persona.prompt_engine import build_character_master_prompt


def build_triage_prompts(
    persona: Persona,
    learned_state: LearnedState,
    triage_prompt: str,
    triage_flags: set[str],
    author: str,
    tweet_text: str,
    is_relationship: bool,
) -> tuple[str, str]:
    master_char_prompt = build_character_master_prompt(persona, action_type="triage", learned_state=learned_state)
    triage_parts = [
        master_char_prompt,
        "",
        "=== TASK DIRECTIVE: TWEET TRIAGE & ENGAGEMENT DECISION ===",
        triage_prompt,
    ]

    system_prompt = "\n".join(triage_parts)
    user_prompt = (
        f"Tweet Details:\n"
        f"Author: @{author}\n"
        f"Text: \"{tweet_text}\"\n"
        f"Is this author a known relationship? {is_relationship}\n\n"
        "Evaluate if you should like, retweet, reply, quote, or skip. "
        "Return a JSON object with this schema:\n"
        "{\n"
        "  \"decision\": {\n"
        "    \"action\": \"like | retweet | reply | quote | skip\",\n"
        "    \"confidence\": 0.0-1.0\n"
        "  }\n"
        "}\n"
    )
    return system_prompt, user_prompt


def build_reply_prompts(
    persona: Persona,
    learned_state: LearnedState,
    relationships: Relationships,
    reply_prompt: str,
    reply_flags: set[str],
    author: str,
    tweet_text: str,
    is_relationship: bool,
) -> tuple[str, str]:
    master_char_prompt = build_character_master_prompt(persona, action_type="reply", learned_state=learned_state)
    reply_parts = [
        master_char_prompt,
        "",
        "=== TASK DIRECTIVE: FEED REPLY GENERATION ===",
        reply_prompt,
        "Write in your unique voice. Do NOT break character.\n",
    ]

    if is_relationship or "memory" in reply_flags:
        rel_notes = relationships.accounts.get(author, "")
        if rel_notes:
            reply_parts.append(f"Relationship with @{author}:\n- {rel_notes}")
            reply_parts.append(
                "Note: Draw on your long-term relationship memory and past experiences to influence your message."
            )

    worldview_block = build_worldview_prompt_section(
        persona,
        context_text=tweet_text,
        is_reply=True,
    )
    if worldview_block:
        reply_parts.append(f"=== SITUATIONAL WORLDVIEW & LINGUISTIC DIRECTIVES ===\n{worldview_block}")

    system_prompt = "\n".join(reply_parts)
    user_prompt = (
        f"Tweet to reply to:\n"
        f"Author: @{author}\n"
        f"Text: \"{tweet_text}\"\n\n"
        f"Generate a highly contextual reply (or quote tweet text) according to your persona.\n"
        "Return a JSON object with this schema:\n"
        "{\n"
        "  \"decision\": {\n"
        "    \"action\": \"reply\",\n"
        "    \"confidence\": 1.0,\n"
        "    \"content\": \"Your reply text here\"\n"
        "  }\n"
        "}\n"
    )
    return system_prompt, user_prompt


def build_follow_prompts(
    persona: Persona,
    target_username: str,
    target_bio: str,
    recent_tweets: list[str],
) -> tuple[str, str]:
    system_prompt = (
        f"You are {persona.display_name} (@{persona.x_handle}). Decide if you should follow a user.\n"
        f"Background: {persona.identity.background}\n"
        f"Interests: {', '.join(persona.interests.primary)}\n"
        f"Networking Goals: Expand influence in your interest areas.\n"
    )

    tweets_str = "\n".join(f"- \"{t}\"" for t in recent_tweets[:5])
    user_prompt = (
        f"Target User Details:\n"
        f"Username: @{target_username}\n"
        f"Bio: \"{target_bio}\"\n"
        f"Recent Tweets:\n{tweets_str}\n\n"
        "Evaluate if you should follow this user based on your persona interests and goals. "
        "Return a JSON object with this schema:\n"
        "{\n"
        "  \"decision\": {\n"
        "    \"should_follow\": true | false,\n"
        "    \"confidence\": 0.0-1.0\n"
        "  }\n"
        "}\n"
    )
    return system_prompt, user_prompt
