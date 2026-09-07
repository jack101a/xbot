import logging
import re
logger = logging.getLogger(__name__)

VALID_ARCHETYPES = {
    "curiosity_gap",
    "contrarian",
    "framework_breakdown",
    "story_relatable",
    "statistical_data",
    "bold_prediction",
}

ARCHETYPE_ALIASES = {
    "curiosity_gap": "curiosity_gap",
    "curiosity-gap": "curiosity_gap",
    "curiosity": "curiosity_gap",
    "contrarian": "contrarian",
    "contrarian_take": "contrarian",
    "framework_breakdown": "framework_breakdown",
    "framework-breakdown": "framework_breakdown",
    "framework": "framework_breakdown",
    "story_relatable": "story_relatable",
    "story-relatable": "story_relatable",
    "story": "story_relatable",
    "relatable": "story_relatable",
    "statistical_data": "statistical_data",
    "statistical-data": "statistical_data",
    "statistical": "statistical_data",
    "data": "statistical_data",
    "data_proof": "statistical_data",
    "bold_prediction": "bold_prediction",
    "bold-prediction": "bold_prediction",
    "prediction": "bold_prediction",
    "future_forecast": "bold_prediction",
}

VALID_VIRAL_ARCHETYPES = {
    "contrarian_reversal",
    "asymmetric_result",
    "zero_to_hero",
    "framework_breakdown",
}

VIRAL_ARCHETYPE_ALIASES = {
    "contrarian": "contrarian_reversal",
    "contrarian_reversal": "contrarian_reversal",
    "contrarian-reversal": "contrarian_reversal",
    "reversal": "contrarian_reversal",
    "asymmetric": "asymmetric_result",
    "asymmetric_result": "asymmetric_result",
    "asymmetric-result": "asymmetric_result",
    "asymmetry": "asymmetric_result",
    "zero_to_hero": "zero_to_hero",
    "zero-to-hero": "zero_to_hero",
    "story": "zero_to_hero",
    "transformation": "zero_to_hero",
    "framework": "framework_breakdown",
    "framework_breakdown": "framework_breakdown",
    "framework-breakdown": "framework_breakdown",
    "breakdown": "framework_breakdown",
    "curiosity_gap": "contrarian_reversal",
    "story_relatable": "zero_to_hero",
    "statistical_data": "asymmetric_result",
    "bold_prediction": "contrarian_reversal",
}

LINK_REGEX = re.compile(r'https?://[^\s)\]"]+|www\.[^\s)\]"]+', re.IGNORECASE)

BOOKMARK_KEYWORDS = {
    "framework", "cheat sheet", "cheatsheet", "swipe file", "checklist",
    "playbook", "template", "roadmap", "architecture", "breakdown",
    "actionable", "step-by-step", "blueprint", "heuristics", "mental model",
    "rules", "guide", "guide to", "tips", "mistakes", "tools", "stack",
    "lessons", "resources", "workflow", "system", "matrix", "scaling",
    "production", "tutorial", "best practices", "deep dive", "how-to", "howto"
}

