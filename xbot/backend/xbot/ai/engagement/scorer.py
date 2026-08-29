from __future__ import annotations

from typing import Any
from xbot.persona import LearnedState, Persona, Relationships


def build_triage_prompts(
    persona: Persona,
    learned_state: LearnedState,
    triage_prompt: str,
    triage_flags: set[str],
    author: str,
    tweet_text: str,
    is_relationship: bool,
) -> tuple[str, str]:
    interest_keywords = persona.interests.primary + persona.interests.secondary
    triage_parts = [
        triage_prompt,
        f"You are {persona.display_name} (@{persona.x_handle}). Decide if you should engage with a tweet.",
    ]

    if "characteristic" in triage_flags:
        triage_parts.append(f"Always Do: {', '.join(persona.rules.always)}")
        triage_parts.append(f"Never Do: {', '.join(persona.rules.never)}")
        if learned_state.characteristics.behavioral_adaptations:
            triage_parts.append(
                "Learned Behavioral Adaptations:\n"
                + "\n".join(f"- {b}" for b in learned_state.characteristics.behavioral_adaptations)
            )
    if "personality" in triage_flags:
        triage_parts.append(f"Traits: {', '.join(persona.personality.traits)}")
        if learned_state.personality.evolving_nuances:
            triage_parts.append(
                "Evolving Nuances:\n"
                + "\n".join(f"- {n}" for n in learned_state.personality.evolving_nuances)
            )
    if "interests" in triage_flags:
        triage_parts.append(f"Interests: {', '.join(interest_keywords)}")
        if learned_state.interests.emerging_topics:
            triage_parts.append(
                f"Learned Emerging Interests: {', '.join(learned_state.interests.emerging_topics)}"
            )
    if "likes" in triage_flags:
        if learned_state.likes.content_preferences:
            triage_parts.append(
                "Learned Likes / Content Preferences:\n"
                + "\n".join(f"- {l}" for l in learned_state.likes.content_preferences)
            )
        if learned_state.likes.author_archetypes:
            triage_parts.append(
                "Favored Author Archetypes:\n"
                + "\n".join(f"- {a}" for a in learned_state.likes.author_archetypes)
            )
    if "dislikes" in triage_flags:
        triage_parts.append(
            f"Will Not Discuss (Negative): {', '.join(persona.interests.will_not_discuss)}"
        )
        if learned_state.dislikes.learned_taboos:
            triage_parts.append(
                "Learned Dislikes / Taboos:\n"
                + "\n".join(f"- {d}" for d in learned_state.dislikes.learned_taboos)
            )

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
    interest_keywords = persona.interests.primary + persona.interests.secondary
    reply_parts = [
        reply_prompt,
        f"You are {persona.display_name} (@{persona.x_handle}). You are replying to a tweet.",
        "Write in your unique voice. Do NOT break character.\n",
        "=== CHARACTER BRIEF ===",
    ]

    if "characteristic" in reply_flags:
        reply_parts.append(f"Occupation/Background: {persona.identity.background}")
        reply_parts.append("Always Do:\n" + "\n".join(f"- {rule}" for rule in persona.rules.always))
        reply_parts.append("Never Do:\n" + "\n".join(f"- {rule}" for rule in persona.rules.never))
        if learned_state.characteristics.behavioral_adaptations:
            reply_parts.append(
                "Learned Behavioral Adaptations:\n"
                + "\n".join(f"- {b}" for b in learned_state.characteristics.behavioral_adaptations)
            )

    if "personality" in reply_flags:
        reply_parts.append(f"Personality Traits: {', '.join(persona.personality.traits)}")
        reply_parts.append(f"Communication Style (Voice context): {persona.personality.communication_style}")
        reply_parts.append(f"Tone: {persona.writing_style.tone}")
        if learned_state.personality.evolving_nuances:
            reply_parts.append(
                "Evolving Nuances:\n"
                + "\n".join(f"- {n}" for n in learned_state.personality.evolving_nuances)
            )

    if "habits" in reply_flags:
        reply_parts.append("Writing Style Heuristics:\n" + "\n".join(f"- {fmt}" for fmt in persona.writing_style.formatting))
        reply_parts.append("Examples of how you write:\n" + "\n".join(f"- \"{ex}\"" for ex in persona.writing_style.examples))
        if learned_state.habits.learned_writing_patterns:
            reply_parts.append(
                "Learned Writing Patterns / Habits:\n"
                + "\n".join(f"- {h}" for h in learned_state.habits.learned_writing_patterns)
            )
        if learned_state.habits.engagement_tactics:
            reply_parts.append(
                "Engagement Tactics:\n"
                + "\n".join(f"- {t}" for t in learned_state.habits.engagement_tactics)
            )

    if "interests" in reply_flags:
        reply_parts.append(f"Interests: {', '.join(interest_keywords)}")
        if learned_state.interests.emerging_topics:
            reply_parts.append(
                f"Learned Emerging Interests: {', '.join(learned_state.interests.emerging_topics)}"
            )
        if learned_state.interests.decaying_topics:
            reply_parts.append(
                f"Avoid Decaying Topics: {', '.join(learned_state.interests.decaying_topics)}"
            )

    if "likes" in reply_flags:
        if learned_state.likes.content_preferences:
            reply_parts.append(
                "Learned Likes / Content Preferences:\n"
                + "\n".join(f"- {l}" for l in learned_state.likes.content_preferences)
            )
        if learned_state.likes.author_archetypes:
            reply_parts.append(
                "Favored Author Archetypes:\n"
                + "\n".join(f"- {a}" for a in learned_state.likes.author_archetypes)
            )

    if "dislikes" in reply_flags:
        reply_parts.append(f"Will Not Discuss: {', '.join(persona.interests.will_not_discuss)}")
        if learned_state.dislikes.learned_taboos:
            reply_parts.append(
                "Learned Dislikes / Taboos:\n"
                + "\n".join(f"- {d}" for d in learned_state.dislikes.learned_taboos)
            )

    if is_relationship or "memory" in reply_flags:
        rel_notes = relationships.accounts.get(author, "")
        if rel_notes:
            reply_parts.append(f"Relationship with @{author}:\n- {rel_notes}")
        reply_parts.append(
            "Note: Draw on your long-term relationship memory and past experiences to influence your message."
        )

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
