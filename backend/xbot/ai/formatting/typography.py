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
            "The M4 Max efficiency gap is actually absurd. Intel needs a miracle.",
            "90% of meetings could be replaced by a clean git diff.",
            "Cinema is so back.",
            "Upgraded to an OLED monitor just to debug stack traces in 4K HDR.",
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
            "Open source won the model layer.\n\nProprietary moats collapsed into distribution and UI.\n\nNow the real war begins.",
            "Shipped the MVP in 3 hours.\n\nSpent 4 days debugging Safari CSS.\n\nNature is healing.",
            "Most startups don't die from competition.\n\nThey die from building 14 features nobody asked for.\n\nSales cures vanity.",
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
            "Junior dev: 'Can we rewrite the entire backend in Rust?'\n\nSenior dev: 'We haven't validated the product in Python yet.'",
            "Founder: 'We are launching stealth AI.'\n\nUsers: 'Can you please just fix the login page?'",
            "Marketing: 'We need 5 approvals before posting.'\n\nCompetitor: *Ships a raw meme and gains 10k users*",
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
            "Look closely at the memory allocation curve in Q3.\n\nThis is where the entire architecture snapped.",
            "the exact moment everything went downhill",
            "One chart that explains why every developer is migrating to local inference.",
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
            "What people think senior engineering is:\nWriting 10,000 lines of complex distributed code.\n\nWhat it actually is:\nDeleting 500 lines of dead code and going home early.",
            "Building in 2022: 6 months to train a classifier.\n\nBuilding in 2026: 1 API call and 3 weeks arguing over system prompt formatting.",
            "Amateurs optimize for output volume.\n\nPros optimize for iteration speed and feedback loops.",
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
            "The 3-step filter before shipping any new feature:\n\n- Does it reduce clicks for power users?\n- Can support explain it in 1 sentence?\n- Will it survive 10x traffic spikes without a refactor?",
            "Why 95% of AI wrappers die within 60 days:\n\n- Zero proprietary data moat\n- Brittle prompt engineering\n- Commoditized user interface\n\nDistribution beats raw features.",
            "Rules for high-signal technical writing:\n\n- Lead with the counter-intuitive result\n- Show the exact command or config\n- Cut every adjective that doesn't add data",
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
            "Code reviews are mostly theater.\n\nIf you need 4 engineers to spot syntax errors, your CI/CD is broken. Reviews should debate architecture, not linting.",
            "Most productivity tools don't save time.\n\nThey just convert procrastination into a structured Kanban board.",
            "The cleanest code is code you never had to write. Engineering discipline is about what you choose to omit.",
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
            "Most teams adopting microservices spend more hours debugging network latency than shipping features.\n\nAre microservices dead for 95% of startups in 2026?",
            "Khan Market cold coffee vs starter home-brewed filter coffee.\n\nWhy do people pretend aesthetics taste better when they cost 450 rupees?",
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
