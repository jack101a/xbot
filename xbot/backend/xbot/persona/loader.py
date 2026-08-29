from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any
from ruamel.yaml import YAML

from .models import (
    AccountRelationship,
    Config,
    ContentStrategyConfig,
    CredentialsConfig,
    EngagementStrategyConfig,
    EngagementTargets,
    FocusConfig,
    Goals,
    Identity,
    Interests,
    LearnedCharacteristics,
    LearnedDislikes,
    LearnedHabits,
    LearnedInterests,
    LearnedLikes,
    LearnedPersonality,
    LearnedState,
    LimitsConfig,
    Persona,
    Personality,
    Relationships,
    Rules,
    ScheduleConfig,
    Strategy,
    TargetKOL,
    KOLChannel,
    WritingStyle,
)

logger = logging.getLogger(__name__)

# Configure ruamel.yaml for safe load/dump
yaml = YAML(typ="safe")
yaml.default_flow_style = False


def load_persona(profile_dir: Path | str) -> Persona:
    """Loads persona.yaml from the given profile directory, slug, or direct file path."""
    p = Path(profile_dir)
    if not p.exists():
        candidate = Path("/home/ubuntu/projects/xbot/data/profiles") / p
        if candidate.exists():
            p = candidate
        else:
            candidate_file = Path("/home/ubuntu/projects/xbot/data/profiles") / p / "persona.yaml"
            if candidate_file.exists():
                p = candidate_file

    if p.is_file() or str(p).endswith(".yaml") or str(p).endswith(".yml"):
        path = p
    else:
        path = p / "persona.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Persona file not found: {path}")
    with path.open(encoding="utf-8") as f:
        data = yaml.load(f)
    return Persona.model_validate(data)


def load_config(profile_dir: Path) -> Config:
    """Loads config.yaml from the given profile directory."""
    path = profile_dir / "config.yaml"
    if not path.exists():
        return Config()
    with path.open(encoding="utf-8") as f:
        data = yaml.load(f)
    return Config.model_validate(data)


def save_config(profile_dir: Path, config: Config) -> None:
    """Saves config.yaml to the given profile directory."""
    profile_dir.mkdir(parents=True, exist_ok=True)
    path = profile_dir / "config.yaml"
    with path.open("w", encoding="utf-8") as f:
        yaml.dump(config.model_dump(), f)


def load_strategy(profile_dir: Path) -> Strategy:
    """Loads strategy.yaml from the given profile directory."""
    path = profile_dir / "strategy.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Strategy file not found: {path}")
    with path.open(encoding="utf-8") as f:
        data = yaml.load(f)
    return Strategy.model_validate(data)


def load_relationships(profile_dir: Path) -> Relationships:
    """Loads known_accounts.yaml from the relationships subdirectory."""
    path = profile_dir / "relationships" / "known_accounts.yaml"
    if not path.exists():
        return Relationships()
    with path.open(encoding="utf-8") as f:
        data = yaml.load(f)
    if not data:
        return Relationships()
    return Relationships.model_validate(data)


def save_strategy(profile_dir: Path, strategy: Strategy) -> None:
    """Saves strategy.yaml to the given profile directory."""
    profile_dir.mkdir(parents=True, exist_ok=True)
    path = profile_dir / "strategy.yaml"
    with path.open("w", encoding="utf-8") as f:
        yaml.dump(strategy.model_dump(), f)


def save_relationships(profile_dir: Path, relationships: Relationships) -> None:
    """Saves known_accounts.yaml to the relationships subdirectory."""
    rel_dir = profile_dir / "relationships"
    rel_dir.mkdir(parents=True, exist_ok=True)
    path = rel_dir / "known_accounts.yaml"
    with path.open("w", encoding="utf-8") as f:
        yaml.dump(relationships.model_dump(), f)


def load_learned_state(profile_dir: Path) -> LearnedState:
    """Loads learned_state.yaml from the given profile directory."""
    path = profile_dir / "learned_state.yaml"
    if not path.exists():
        return LearnedState()
    with path.open(encoding="utf-8") as f:
        data = yaml.load(f)
    if not data:
        return LearnedState()
    return LearnedState.model_validate(data)


def save_learned_state(profile_dir: Path, state: LearnedState) -> None:
    """Saves learned_state.yaml to the given profile directory."""
    profile_dir.mkdir(parents=True, exist_ok=True)
    path = profile_dir / "learned_state.yaml"
    with path.open("w", encoding="utf-8") as f:
        yaml.dump(state.model_dump(), f)


def save_persona(profile_dir: Path | str, persona: Persona) -> None:
    """Saves persona.yaml to the given profile directory."""
    p = Path(profile_dir)
    path = p if (p.is_file() or str(p).endswith(".yaml")) else p / "persona.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        yaml.dump(persona.model_dump(), f)


def load_character_card(profile_dir: Path | str) -> dict[str, Any]:
    """Loads character_card.json if present."""
    p = Path(profile_dir)
    card_path = p if str(p).endswith(".json") else p / "character_card.json"
    if not card_path.exists():
        return {}
    with card_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_character_card(profile_dir: Path | str, card_data: dict[str, Any]) -> None:
    """Saves character_card.json to the profile directory."""
    p = Path(profile_dir)
    card_path = p if str(p).endswith(".json") else p / "character_card.json"
    card_path.parent.mkdir(parents=True, exist_ok=True)
    with card_path.open("w", encoding="utf-8") as f:
        json.dump(card_data, f, indent=2)


__all__ = [
    "AccountRelationship",
    "Config",
    "ContentStrategyConfig",
    "CredentialsConfig",
    "EngagementStrategyConfig",
    "EngagementTargets",
    "FocusConfig",
    "Goals",
    "Identity",
    "Interests",
    "LearnedCharacteristics",
    "LearnedDislikes",
    "LearnedHabits",
    "LearnedInterests",
    "LearnedLikes",
    "LearnedPersonality",
    "LearnedState",
    "LimitsConfig",
    "Persona",
    "Personality",
    "Relationships",
    "Rules",
    "ScheduleConfig",
    "Strategy",
    "TargetKOL",
    "WritingStyle",
    "load_character_card",
    "load_config",
    "load_learned_state",
    "load_persona",
    "load_relationships",
    "load_strategy",
    "save_character_card",
    "save_config",
    "save_learned_state",
    "save_persona",
    "save_relationships",
    "save_strategy",
    "yaml",
]
