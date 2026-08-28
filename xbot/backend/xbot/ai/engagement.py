from __future__ import annotations

import json
import logging
import random
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from xbot.ai.client import get_ai_client
from xbot.config import settings
from xbot.models.profile import Profile, RateLimit
from xbot.persona import load_config, load_persona, load_relationships, load_learned_state

logger = logging.getLogger(__name__)


class EngagementDecision(BaseModel):
    action: Literal["like", "retweet", "reply", "quote", "skip"]
    confidence: float = Field(..., ge=0.0, le=1.0)
    content: str | None = Field(default=None, description="In-character text if reply/quote, null otherwise")

class TriageDecision(BaseModel):
    action: Literal["like", "retweet", "reply", "quote", "skip"]
    confidence: float = Field(..., ge=0.0, le=1.0)

class FollowDecision(BaseModel):
    should_follow: bool
    confidence: float = Field(..., ge=0.0, le=1.0)


class EngagementResponse(BaseModel):
    decision: EngagementDecision

class TriageResponse(BaseModel):
    decision: TriageDecision

class FollowResponse(BaseModel):
    decision: FollowDecision


class EngagementEvaluator:
    """
    Implements the Engagement Decision Flow.
    Checks relationships, interest keywords, calls the fast model (MODEL_LIKE_RETWEET) for triage,
    and applies database rate limit budget checks/downgrades.
    If the decision is reply/quote, it then uses MODEL_REPLY_ANALYSIS to generate the content.
    """

    def __init__(
        self, base_profile_dir: str = "/home/ubuntu/projects/xbot/data/profiles"
    ) -> None:
        self.base_profile_dir = Path(base_profile_dir)

    async def evaluate_engagement(
        self,
        db: AsyncSession,
        profile_slug: str,
        tweet: dict[str, Any],
    ) -> EngagementDecision:
        """
        Processes a single tweet and determines what action (like, retweet, reply, quote, skip)
        the persona should take towards it.
        """
        # 1. Fetch Profile
        stmt = select(Profile).where(Profile.profile_slug == profile_slug)
        res = await db.execute(stmt)
        profile = res.scalar_one_or_none()
        if not profile:
            raise ValueError(f"Profile with slug '{profile_slug}' not found.")

        profile_dir = self.base_profile_dir / profile_slug
        persona = load_persona(profile_dir)
        config = load_config(profile_dir)
        relationships = load_relationships(profile_dir)
        learned_state = load_learned_state(profile_dir)

        # Job Overrides
        profile_config = profile.config or {}
        job_overrides = profile_config.get("job_routing_overrides", {})
        
        # Like/Retweet (Triage) Configuration
        triage_model = job_overrides.get("MODEL_LIKE_RETWEET") or settings.MODEL_LIKE_RETWEET
        triage_prompt = job_overrides.get("PROMPT_LIKE_RETWEET") or settings.PROMPT_LIKE_RETWEET
        triage_context = job_overrides.get("CONTEXT_LIKE_RETWEET") or settings.CONTEXT_LIKE_RETWEET
        triage_flags = set(triage_context.split(","))
        
        # Reply/Quote Configuration
        reply_model = job_overrides.get("MODEL_REPLY_ANALYSIS") or settings.MODEL_REPLY_ANALYSIS
        reply_prompt = job_overrides.get("PROMPT_REPLY_ANALYSIS") or settings.PROMPT_REPLY_ANALYSIS
        reply_context = job_overrides.get("CONTEXT_REPLY_ANALYSIS") or settings.CONTEXT_REPLY_ANALYSIS
        reply_flags = set(reply_context.split(","))

        author = tweet.get("author", "").strip().lstrip("@")
        tweet_text = tweet.get("text", "")

        # A. Check known relationships
        is_relationship = author.lower() in {name.lower() for name in relationships.accounts.keys()}

        # B. Check interest areas
        interest_keywords = persona.interests.primary + persona.interests.secondary
        in_interest_area = any(kw.lower() in tweet_text.lower() for kw in interest_keywords)

        # Heuristic shortcut for non-interest / non-relationship tweets
        if not is_relationship and not in_interest_area:
            logger.info("Tweet is outside interests and relationships. Applying heuristics.")
            if random.random() < 0.8:
                return EngagementDecision(action="skip", confidence=0.8)
            else:
                decision = EngagementDecision(action="like", confidence=0.2)
                return await self._apply_rate_budget_check(db, profile.id, config, decision)

        client = get_ai_client()

        # C. Fast Triage Decision using MODEL_LIKE_RETWEET
        triage_parts = [
            triage_prompt,
            f"You are {persona.display_name} (@{persona.x_handle}). Decide if you should engage with a tweet."
        ]
        
        if "characteristic" in triage_flags:
            triage_parts.append(f"Always Do: {', '.join(persona.rules.always)}")
            triage_parts.append(f"Never Do: {', '.join(persona.rules.never)}")
            if learned_state.characteristics.behavioral_adaptations:
                triage_parts.append("Learned Behavioral Adaptations:\n" + "\n".join(f"- {b}" for b in learned_state.characteristics.behavioral_adaptations))
        if "personality" in triage_flags:
            triage_parts.append(f"Traits: {', '.join(persona.personality.traits)}")
            if learned_state.personality.evolving_nuances:
                triage_parts.append("Evolving Nuances:\n" + "\n".join(f"- {n}" for n in learned_state.personality.evolving_nuances))
        if "interests" in triage_flags:
            triage_parts.append(f"Interests: {', '.join(interest_keywords)}")
            if learned_state.interests.emerging_topics:
                triage_parts.append(f"Learned Emerging Interests: {', '.join(learned_state.interests.emerging_topics)}")
        if "likes" in triage_flags:
            if learned_state.likes.content_preferences:
                triage_parts.append("Learned Likes / Content Preferences:\n" + "\n".join(f"- {l}" for l in learned_state.likes.content_preferences))
            if learned_state.likes.author_archetypes:
                triage_parts.append("Favored Author Archetypes:\n" + "\n".join(f"- {a}" for a in learned_state.likes.author_archetypes))
        if "dislikes" in triage_flags:
            triage_parts.append(f"Will Not Discuss (Negative): {', '.join(persona.interests.will_not_discuss)}")
            if learned_state.dislikes.learned_taboos:
                triage_parts.append("Learned Dislikes / Taboos:\n" + "\n".join(f"- {d}" for d in learned_state.dislikes.learned_taboos))
            
        triage_system_prompt = "\n".join(triage_parts)
        
        triage_user_prompt = (
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

        try:
            try:
                completion = await client.beta.chat.completions.parse(
                    model=triage_model,
                    messages=[
                        {"role": "system", "content": triage_system_prompt},
                        {"role": "user", "content": triage_user_prompt},
                    ],
                    response_format=TriageResponse,
                )
                parsed = completion.choices[0].message.parsed
                if parsed and parsed.decision:
                    action = parsed.decision.action
                    confidence = parsed.decision.confidence
                else:
                    raise ValueError("No triage decision parsed.")
            except Exception as e:
                logger.warning("Beta chat parse for triage failed, falling back: %s", e)
                completion = await client.chat.completions.create(
                    model=triage_model,
                    messages=[
                        {"role": "system", "content": triage_system_prompt},
                        {"role": "user", "content": triage_user_prompt},
                    ],
                    response_format={"type": "json_object"},
                )
                raw_text = completion.choices[0].message.content or ""
                cleaned_text = raw_text.strip()
                if cleaned_text.startswith("```json"):
                    cleaned_text = cleaned_text[7:]
                if cleaned_text.endswith("```"):
                    cleaned_text = cleaned_text[:-3]
                data = json.loads(cleaned_text.strip())
                parsed_obj = TriageResponse.model_validate(data)
                action = parsed_obj.decision.action
                confidence = parsed_obj.decision.confidence
        except Exception as e:
            logger.error("Fast triage evaluation failed: %s. Defaulting to skip.", e)
            action = "skip"
            confidence = 1.0

        impressions = int(tweet.get("impressions", 0) or tweet.get("views", 0) or 0)
        # Enforce min 50k views rule for quote-tweeting
        if action == "quote":
            if 0 < impressions < 50_000:
                logger.info("Downgrading quote to reply: tweet has %d views (< 50k minimum for quote-tweets)", impressions)
                action = "reply"

        decision = EngagementDecision(action=action, confidence=confidence, content=None)

        # Check limits early to avoid generating content if not needed
        decision = await self._apply_rate_budget_check(db, profile.id, config, decision)
        
        # D. Heavy Generation for Reply/Quote using MODEL_REPLY_ANALYSIS
        if decision.action in ("reply", "quote"):
            reply_parts = [
                reply_prompt,
                f"You are {persona.display_name} (@{persona.x_handle}). You are replying to a tweet.",
                "Write in your unique voice. Do NOT break character.\n",
                "=== CHARACTER BRIEF ==="
            ]
            
            if "characteristic" in reply_flags:
                reply_parts.append(f"Occupation/Background: {persona.identity.background}")
                reply_parts.append("Always Do:\n" + "\n".join(f"- {rule}" for rule in persona.rules.always))
                reply_parts.append("Never Do:\n" + "\n".join(f"- {rule}" for rule in persona.rules.never))
                if learned_state.characteristics.behavioral_adaptations:
                    reply_parts.append("Learned Behavioral Adaptations:\n" + "\n".join(f"- {b}" for b in learned_state.characteristics.behavioral_adaptations))
                
            if "personality" in reply_flags:
                reply_parts.append(f"Personality Traits: {', '.join(persona.personality.traits)}")
                reply_parts.append(f"Communication Style (Voice context): {persona.personality.communication_style}")
                reply_parts.append(f"Tone: {persona.writing_style.tone}")
                if learned_state.personality.evolving_nuances:
                    reply_parts.append("Evolving Nuances:\n" + "\n".join(f"- {n}" for n in learned_state.personality.evolving_nuances))
                
            if "habits" in reply_flags:
                reply_parts.append("Writing Style Heuristics:\n" + "\n".join(f"- {fmt}" for fmt in persona.writing_style.formatting))
                reply_parts.append("Examples of how you write:\n" + "\n".join(f"- \"{ex}\"" for ex in persona.writing_style.examples))
                if learned_state.habits.learned_writing_patterns:
                    reply_parts.append("Learned Writing Patterns / Habits:\n" + "\n".join(f"- {h}" for h in learned_state.habits.learned_writing_patterns))
                if learned_state.habits.engagement_tactics:
                    reply_parts.append("Engagement Tactics:\n" + "\n".join(f"- {t}" for t in learned_state.habits.engagement_tactics))
                
            if "interests" in reply_flags:
                reply_parts.append(f"Interests: {', '.join(interest_keywords)}")
                if learned_state.interests.emerging_topics:
                    reply_parts.append(f"Learned Emerging Interests: {', '.join(learned_state.interests.emerging_topics)}")
                if learned_state.interests.decaying_topics:
                    reply_parts.append(f"Avoid Decaying Topics: {', '.join(learned_state.interests.decaying_topics)}")
                
            if "likes" in reply_flags:
                if learned_state.likes.content_preferences:
                    reply_parts.append("Learned Likes / Content Preferences:\n" + "\n".join(f"- {l}" for l in learned_state.likes.content_preferences))
                if learned_state.likes.author_archetypes:
                    reply_parts.append("Favored Author Archetypes:\n" + "\n".join(f"- {a}" for a in learned_state.likes.author_archetypes))

            if "dislikes" in reply_flags:
                reply_parts.append(f"Will Not Discuss: {', '.join(persona.interests.will_not_discuss)}")
                if learned_state.dislikes.learned_taboos:
                    reply_parts.append("Learned Dislikes / Taboos:\n" + "\n".join(f"- {d}" for d in learned_state.dislikes.learned_taboos))
                
            if is_relationship or "memory" in reply_flags:
                rel_notes = relationships.accounts.get(author, "")
                if rel_notes:
                    reply_parts.append(f"Relationship with @{author}:\n- {rel_notes}")
                reply_parts.append("Note: Draw on your long-term relationship memory and past experiences to influence your message.")
                
            reply_system_prompt = "\n".join(reply_parts)

            reply_user_prompt = (
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
            
            try:
                try:
                    completion = await client.beta.chat.completions.parse(
                        model=reply_model,
                        messages=[
                            {"role": "system", "content": reply_system_prompt},
                            {"role": "user", "content": reply_user_prompt},
                        ],
                        response_format=EngagementResponse,
                    )
                    parsed = completion.choices[0].message.parsed
                    if parsed and parsed.decision and parsed.decision.content:
                        decision.content = parsed.decision.content
                    else:
                        raise ValueError("No reply content parsed.")
                except Exception as e:
                    completion = await client.chat.completions.create(
                        model=reply_model,
                        messages=[
                            {"role": "system", "content": reply_system_prompt},
                            {"role": "user", "content": reply_user_prompt},
                        ],
                        response_format={"type": "json_object"},
                    )
                    raw_text = completion.choices[0].message.content or ""
                    cleaned_text = raw_text.strip()
                    if cleaned_text.startswith("```json"):
                        cleaned_text = cleaned_text[7:]
                    if cleaned_text.endswith("```"):
                        cleaned_text = cleaned_text[:-3]
                    data = json.loads(cleaned_text.strip())
                    parsed_obj = EngagementResponse.model_validate(data)
                    decision.content = parsed_obj.decision.content
            except Exception as e:
                logger.error("Heavy reply generation failed: %s. Downgrading to like.", e)
                decision.action = "like"
                decision.content = None

        return decision

    async def _apply_rate_budget_check(
        self,
        db: AsyncSession,
        profile_id: Any,
        config: Any,
        decision: EngagementDecision,
    ) -> EngagementDecision:
        """Enforces limits by downgrading quote->reply->like->skip based on remaining rate limits."""
        action = decision.action
        if action == "skip":
            return decision

        # Check reply limits (replies + quotes)
        if action in ("reply", "quote"):
            stmt = select(RateLimit).where(
                RateLimit.profile_id == profile_id,
                RateLimit.action_type == "reply",
            )
            res = await db.execute(stmt)
            lim_reply = res.scalar_one_or_none()
            used_replies = lim_reply.count_today if lim_reply else 0
            limit_replies = config.limits.max_replies_per_day

            if used_replies >= limit_replies:
                logger.info("Reply rate limit hit (%d/%d). Downgrading to like.", used_replies, limit_replies)
                action = "like"
                decision.action = "like"
                decision.content = None

        # Check like limits
        if action == "like":
            stmt = select(RateLimit).where(
                RateLimit.profile_id == profile_id,
                RateLimit.action_type == "like",
            )
            res = await db.execute(stmt)
            lim_like = res.scalar_one_or_none()
            used_likes = lim_like.count_today if lim_like else 0
            limit_likes = config.limits.max_likes_per_day

            if used_likes >= limit_likes:
                logger.info("Like rate limit hit (%d/%d). Downgrading to skip.", used_likes, limit_likes)
                action = "skip"
                decision.action = "skip"
                decision.content = None

        return decision


class FollowEvaluator:
    """
    Evaluates whether a target profile is worth following using MODEL_FOLLOW.
    """

    def __init__(
        self, base_profile_dir: str = "/home/ubuntu/projects/xbot/data/profiles"
    ) -> None:
        self.base_profile_dir = Path(base_profile_dir)

    async def evaluate_follow(
        self,
        db: AsyncSession,
        profile_slug: str,
        target_username: str,
        target_bio: str,
        recent_tweets: list[str],
    ) -> bool:
        """
        Determines if the persona should follow the target user.
        """
        # 1. Fetch Profile
        stmt = select(Profile).where(Profile.profile_slug == profile_slug)
        res = await db.execute(stmt)
        profile = res.scalar_one_or_none()
        if not profile:
            raise ValueError(f"Profile with slug '{profile_slug}' not found.")

        profile_dir = self.base_profile_dir / profile_slug
        persona = load_persona(profile_dir)
        
        client = get_ai_client()

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

        try:
            try:
                completion = await client.beta.chat.completions.parse(
                    model=settings.MODEL_FOLLOW,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    response_format=FollowResponse,
                )
                parsed = completion.choices[0].message.parsed
                if parsed and parsed.decision:
                    return parsed.decision.should_follow
                else:
                    return False
            except Exception as e:
                completion = await client.chat.completions.create(
                    model=settings.MODEL_FOLLOW,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    response_format={"type": "json_object"},
                )
                raw_text = completion.choices[0].message.content or ""
                cleaned_text = raw_text.strip()
                if cleaned_text.startswith("```json"):
                    cleaned_text = cleaned_text[7:]
                if cleaned_text.endswith("```"):
                    cleaned_text = cleaned_text[:-3]
                data = json.loads(cleaned_text.strip())
                parsed_obj = FollowResponse.model_validate(data)
                return parsed_obj.decision.should_follow
        except Exception as e:
            logger.error("Follow evaluation failed: %s. Defaulting to false.", e)
            return False

