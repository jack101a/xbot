from __future__ import annotations

from enum import Enum
import logging
import random
from typing import Sequence
from pydantic import BaseModel
from xbot.persona.loader import Persona

logger = logging.getLogger(__name__)


class PostFormattingArchetype(str, Enum):
    MICRO_PUNCHLINE = "MICRO_PUNCHLINE"
    STACCATO_OBSERVATION = "STACCATO_OBSERVATION"
    SCENARIO_DIALOGUE = "SCENARIO_DIALOGUE"
    MEDIA_SETUP_HOOK = "MEDIA_SETUP_HOOK"
    CONTRAST_BLOCKS = "CONTRAST_BLOCKS"
    MINI_LIST_FRAMEWORK = "MINI_LIST_FRAMEWORK"
    HOT_TAKE_PUNCH = "HOT_TAKE_PUNCH"
    DEBATE_DILEMMA = "DEBATE_DILEMMA"


class ArchetypeSpec(BaseModel):
    archetype: PostFormattingArchetype
    display_name: str
    min_chars: int
    max_chars: int
    ideal_chars: int
    requires_media: bool = False
    directives: str
    few_shot_examples: list[str]


ARCHETYPE_REGISTRY: dict[PostFormattingArchetype, ArchetypeSpec] = {
    PostFormattingArchetype.MICRO_PUNCHLINE: ArchetypeSpec(
        archetype=PostFormattingArchetype.MICRO_PUNCHLINE,
        display_name="Micro Punchline",
        min_chars=20,
        max_chars=85,
        ideal_chars=50,
        directives=(
            "FORMAT: MICRO_PUNCHLINE (20-85 chars total).\n"
            "- Exactly 1 single sentence or short 2-clause punchline.\n"
            "- High conviction, dry irony, or deadpan observation.\n"
            "- Zero introductory filler and no trailing hashtags or trailing emojis."
        ),
        few_shot_examples=[
            "The hype around every new phone launch dies the exact second you put a $5 plastic case on it.",
            "90% of online arguments could be resolved if people actually watched the full 30-second clip.",
            "Cinema is so back.",
            "Bought a high-end monitor for 'focus' and now I just watch 4K IMAX trailers with zero regrets.",
        ],
    ),
    PostFormattingArchetype.STACCATO_OBSERVATION: ArchetypeSpec(
        archetype=PostFormattingArchetype.STACCATO_OBSERVATION,
        display_name="Staccato Observation",
        min_chars=80,
        max_chars=180,
        ideal_chars=130,
        directives=(
            "FORMAT: STACCATO_OBSERVATION (80-180 chars total).\n"
            "- Exactly 3 isolated beats separated by double line breaks (\\n\\n).\n"
            "- Line 1: Hook / Premise\n"
            "- Line 2: Real-world friction or elaboration\n"
            "- Line 3: Razor-sharp punchline or kicker\n"
            "- No corporate transitions ('Furthermore', 'In conclusion')."
        ),
        few_shot_examples=[
            "Spent 4 hours setting up aesthetic lighting.\n\nEdited the color grade for 2 hours.\n\nBest performing post of the week was a 3-second blurry selfie.",
            "Every platform is trying to become TikTok.\n\nTikTok is trying to become Amazon.\n\nNobody is having fun anymore.",
            "Most trends don't die from lack of interest.\n\nThey die because brands start making corporate LinkedIn posts about them.\n\nCringe is lethal.",
        ],
    ),
    PostFormattingArchetype.SCENARIO_DIALOGUE: ArchetypeSpec(
        archetype=PostFormattingArchetype.SCENARIO_DIALOGUE,
        display_name="Scenario Dialogue",
        min_chars=90,
        max_chars=200,
        ideal_chars=145,
        directives=(
            "FORMAT: SCENARIO_DIALOGUE (90-200 chars total).\n"
            "- 2 to 3 line conversational script (Role 1: ...\\n\\nRole 2: ...).\n"
            "- Highlight humorous friction, relatable trade-offs, or stark contrast.\n"
            "- Clean punctuation and natural creator tone."
        ),
        few_shot_examples=[
            "Tech brand: 'We integrated generative AI into this blender.'\n\nConsumers: 'Can you please just make the motor last more than 18 months?'",
            "Streamer: 'We need 4 cameras and studio soundproofing.'\n\nAudience: 'Can you please fix the echo on your mic?'",
            "Studio: 'We spent $200M on CGI explosions.'\n\nAudience: 'Why is the dialogue inaudible under the bass?'",
        ],
    ),
    PostFormattingArchetype.MEDIA_SETUP_HOOK: ArchetypeSpec(
        archetype=PostFormattingArchetype.MEDIA_SETUP_HOOK,
        display_name="Media Setup Hook",
        min_chars=15,
        max_chars=90,
        ideal_chars=45,
        requires_media=True,
        directives=(
            "FORMAT: MEDIA_SETUP_HOOK (15-90 chars total).\n"
            "- 1-2 lines framing the attached image or media.\n"
            "- Guide the viewer's eye to the unexpected detail ('Look closely at the bottom curve...').\n"
            "- Never describe what is already obvious; let the visual deliver 80% of the punchline."
        ),
        few_shot_examples=[
            "Look closely at the background reflection in frame 2.\n\nPure unscripted chaos.",
            "the exact moment everyone knew the trailer was going to break the internet",
            "One photo that perfectly captures modern internet culture.",
            "no notes.",
        ],
    ),
    PostFormattingArchetype.CONTRAST_BLOCKS: ArchetypeSpec(
        archetype=PostFormattingArchetype.CONTRAST_BLOCKS,
        display_name="Contrast Blocks",
        min_chars=110,
        max_chars=220,
        ideal_chars=165,
        directives=(
            "FORMAT: CONTRAST_BLOCKS (110-220 chars total).\n"
            "- Two distinct comparison blocks separated by clean double line breaks (\\n\\n).\n"
            "- Format as 'Expectation vs Reality', 'Before vs After', or '2020 vs 2026'.\n"
            "- Crisp, balanced symmetry."
        ),
        few_shot_examples=[
            "What people think content creation is:\nFilming aesthetic b-roll on a quiet balcony.\n\nWhat it actually is:\n4 hours arguing with video export codecs and audio syncing.",
            "Streaming in 2020: One subscription for all the movies you love.\n\nStreaming in 2026: 7 different tiers to rent a 15-year-old movie with ads.",
            "Amateurs optimize for vanity metrics.\n\nReal creators optimize for people who actually care when you post.",
        ],
    ),
    PostFormattingArchetype.MINI_LIST_FRAMEWORK: ArchetypeSpec(
        archetype=PostFormattingArchetype.MINI_LIST_FRAMEWORK,
        display_name="Mini List Framework",
        min_chars=130,
        max_chars=260,
        ideal_chars=195,
        directives=(
            "FORMAT: MINI_LIST_FRAMEWORK (130-260 chars total).\n"
            "- 1 crisp premise line followed by \\n\\n.\n"
            "- Exactly 2 to 3 bullet items using standard '-' or '•' separated by single \\n.\n"
            "- STRICTLY NO emoji bullet headers (no 🚀, 💡, 🔥, ❌, ✅ at start of lines).\n"
            "- 1 short closing rule."
        ),
        few_shot_examples=[
            "The 3-stage cycle of modern social media:\n\n- Genuine creators build an authentic community\n- Algorithms force everyone into short-form engagement farming\n- Everyone migrates to group chats\n\nCycle repeats.",
            "Why most aesthetic hardware setups fail after a week:\n\n- Cable management impossible to maintain\n- Matte surfaces show every fingerprint\n- Comfort sacrificed for minimalism\n\nUsability always wins.",
            "Rules for watching a 3-hour cinema epic:\n\n- Zero liquids 1 hour before showtime\n- Center seat on the IMAX screen\n- Turn off your phone completely",
        ],
    ),
    PostFormattingArchetype.HOT_TAKE_PUNCH: ArchetypeSpec(
        archetype=PostFormattingArchetype.HOT_TAKE_PUNCH,
        display_name="Hot Take Punch",
        min_chars=90,
        max_chars=200,
        ideal_chars=150,
        directives=(
            "FORMAT: HOT_TAKE_PUNCH (90-200 chars total).\n"
            "- Bold contrarian thesis in the opening line.\n"
            "- 1-2 sentences of empirical rationale separated by \\n\\n.\n"
            "- Decisive, confident conclusion with zero corporate waffle."
        ),
        few_shot_examples=[
            "Smartphone camera hardware peaked two years ago.\n\nNow brands are just adding heavier AI filters that make normal faces look like waxy oil paintings. Bring back optical honesty.",
            "Most productivity apps do not save time.\n\nThey just convert normal procrastination into an aesthetically pleasing checklist.",
            "The best movie sequels are the ones nobody asked for that completely subvert expectations.",
        ],
    ),
    PostFormattingArchetype.DEBATE_DILEMMA: ArchetypeSpec(
        archetype=PostFormattingArchetype.DEBATE_DILEMMA,
        display_name="Debate Dilemma",
        min_chars=80,
        max_chars=190,
        ideal_chars=135,
        directives=(
            "FORMAT: DEBATE_DILEMMA (80-190 chars total).\n"
            "- Provocative observation in line 1 followed by \\n\\n.\n"
            "- High-conviction debate question in line 2 ending with '?' compelling replies."
        ),
        few_shot_examples=[
            "People spend 45 minutes scrolling Netflix menus only to fall asleep 10 minutes into a show.\n\nDid streaming platforms engineer choice paralysis on purpose?",
            "Khan Market cold coffee vs home-brewed filter coffee.\n\nWhy do people pretend aesthetics taste better when they cost 450 rupees?",
        ],
    ),
}


def select_archetype(
    topic: str,
    has_media: bool = False,
    persona: Persona | None = None,
    recent_archetypes: Sequence[PostFormattingArchetype | str] | None = None,
    content_type: str = "post",
) -> PostFormattingArchetype:
    """
    Selects a formatting archetype dynamically using contextual rules and anti-monotony cooldown.
    """
    weights: dict[PostFormattingArchetype, float] = {
        PostFormattingArchetype.MICRO_PUNCHLINE: 15.0,
        PostFormattingArchetype.STACCATO_OBSERVATION: 18.0,
        PostFormattingArchetype.SCENARIO_DIALOGUE: 12.0,
        PostFormattingArchetype.MEDIA_SETUP_HOOK: 5.0,
        PostFormattingArchetype.CONTRAST_BLOCKS: 18.0,
        PostFormattingArchetype.MINI_LIST_FRAMEWORK: 16.0,
        PostFormattingArchetype.HOT_TAKE_PUNCH: 18.0,
        PostFormattingArchetype.DEBATE_DILEMMA: 14.0,
    }

    if has_media:
        weights[PostFormattingArchetype.MEDIA_SETUP_HOOK] = 65.0
        weights[PostFormattingArchetype.MICRO_PUNCHLINE] = 20.0
        weights[PostFormattingArchetype.CONTRAST_BLOCKS] = 15.0
        weights[PostFormattingArchetype.MINI_LIST_FRAMEWORK] = 0.0
        weights[PostFormattingArchetype.SCENARIO_DIALOGUE] = 0.0
        weights[PostFormattingArchetype.STACCATO_OBSERVATION] = 0.0
        weights[PostFormattingArchetype.HOT_TAKE_PUNCH] = 0.0
        weights[PostFormattingArchetype.DEBATE_DILEMMA] = 0.0

    topic_lower = topic.lower()
    if any(k in topic_lower for k in [" vs ", "versus", "compared to", "difference", "before after", "reality vs", "then vs"]):
        weights[PostFormattingArchetype.CONTRAST_BLOCKS] += 35.0
    if any(k in topic_lower for k in ["how to", "guide", "rules", "framework", "steps", "checklist", "reasons"]):
        weights[PostFormattingArchetype.MINI_LIST_FRAMEWORK] += 35.0
    if any(k in topic_lower for k in ["unpopular", "overrated", "underrated", "truth", "myth", "dead", "mistake"]):
        weights[PostFormattingArchetype.HOT_TAKE_PUNCH] += 35.0
    if any(k in topic_lower for k in ["meeting", "boss", "interview", "client", "engineer", "designer", "founder"]):
        weights[PostFormattingArchetype.SCENARIO_DIALOGUE] += 30.0
    if any(k in topic_lower for k in ["poll", "which", "would you", "debate", "agree", "disagree"]):
        weights[PostFormattingArchetype.DEBATE_DILEMMA] += 35.0

    # Anti-monotony cooldown
    if recent_archetypes:
        for idx, raw_arch in enumerate(reversed(recent_archetypes)):
            try:
                prev_arch = PostFormattingArchetype(raw_arch)
            except Exception:
                continue
            if prev_arch in weights:
                if idx == 0:
                    weights[prev_arch] = 0.0  # Zero consecutive repetition
                elif idx == 1:
                    weights[prev_arch] *= 0.20
                elif idx == 2:
                    weights[prev_arch] *= 0.50

    population = list(weights.keys())
    w_values = [max(0.0, weights[k]) for k in population]
    if sum(w_values) <= 0:
        return PostFormattingArchetype.HOT_TAKE_PUNCH

    return random.choices(population, weights=w_values, k=1)[0]
