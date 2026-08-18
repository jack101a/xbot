from __future__ import annotations

from pathlib import Path

from ruamel.yaml import YAML

from xbot.persona import (
    DiaryManager,
    MemoryManager,
    load_config,
    load_persona,
    load_relationships,
    load_strategy,
    save_relationships,
    save_strategy,
)
from xbot.persona.loader import (
    AccountRelationship,
    ContentStrategyConfig,
    EngagementStrategyConfig,
    EngagementTargets,
    FocusConfig,
    Relationships,
    Strategy,
    TargetKOL,
)

yaml = YAML(typ="safe")
yaml.default_flow_style = False


def test_yaml_loader_and_saver(tmp_path: Path) -> None:
    # 1. Create a dummy persona.yaml
    persona_data = {
        "id": "test_persona",
        "display_name": "Test Persona",
        "x_handle": "@test_persona",
        "identity": {
            "age": 25,
            "location": "Seattle, WA",
            "occupation": "Automated Test Agent",
            "education": "Digital Sandbox",
            "background": "Designed to verify YAML parsing operations.",
        },
        "personality": {
            "traits": ["precise", "tireless"],
            "values": ["correctness"],
            "communication_style": "Clear, uppercase first letters.",
        },
        "interests": {
            "primary": ["pytests", "mocking"],
            "secondary": ["assertions"],
            "will_not_discuss": ["politics"],
        },
        "writing_style": {
            "tone": "objective",
            "typical_length": "1 sentence",
            "formatting": ["no emojis"],
            "examples": ["Testing is successful."],
        },
        "goals": {
            "short_term": ["Pass all tests"],
            "long_term": ["Achieve 100% test coverage"],
            "content_pillars": ["Quality Assurance (100%)"],
        },
        "rules": {
            "always": ["stay in sandbox"],
            "never": ["touch real web"],
        },
    }
    persona_path = tmp_path / "persona.yaml"
    with persona_path.open("w", encoding="utf-8") as f:
        yaml.dump(persona_data, f)

    # Load and verify
    persona = load_persona(tmp_path)
    assert persona.id == "test_persona"
    assert persona.identity.age == 25
    assert "precise" in persona.personality.traits

    # 2. Verify load_config fallback and loaded defaults
    config = load_config(tmp_path)
    assert config.schedule.min_sessions_per_day == 3
    assert config.limits.max_likes_per_day == 50

    # Write custom config
    config_data = {
        "schedule": {
            "timezone": "Europe/London",
            "active_hours": "09:00-17:00",
            "min_sessions_per_day": 2,
            "max_sessions_per_day": 4,
        },
        "limits": {
            "max_likes_per_day": 20,
            "max_replies_per_day": 5,
        },
    }
    with (tmp_path / "config.yaml").open("w", encoding="utf-8") as f:
        yaml.dump(config_data, f)
    config = load_config(tmp_path)
    assert config.schedule.timezone == "Europe/London"
    assert config.limits.max_likes_per_day == 20
    assert config.limits.max_posts_per_day == 5  # Default value holds

    # 3. Strategy Save & Load
    strategy = Strategy(
        last_updated="2026-06-18",
        current_focus=FocusConfig(primary="Testing Persona Loader"),
        content_strategy=ContentStrategyConfig(
            posting_frequency="1 per day",
            best_times=["12:00"],
            top_performing_topics=["Python"],
            underperforming_topics=["Bugs"],
        ),
        engagement_strategy=EngagementStrategyConfig(
            daily_targets=EngagementTargets(likes="5", replies="2", follows="1"),
            priority_accounts=["@pytest_official"],
        ),
        growth_observations=["More tests = more trust."],
        adjustments=["Keep testing."],
    )
    save_strategy(tmp_path, strategy)
    loaded_strat = load_strategy(tmp_path)
    assert loaded_strat.last_updated == "2026-06-18"
    assert loaded_strat.current_focus.primary == "Testing Persona Loader"

    # 4. Relationships Save & Load
    rel = Relationships(
        accounts={
            "tester_bob": AccountRelationship(
                display_name="Bob the Tester",
                first_seen="2026-06-18",
                relationship="colleague",
                sentiment="highly positive",
                interaction_count=5,
            )
        }
    )
    save_relationships(tmp_path, rel)
    loaded_rel = load_relationships(tmp_path)
    assert "tester_bob" in loaded_rel.accounts
    assert loaded_rel.accounts["tester_bob"].display_name == "Bob the Tester"
    assert loaded_rel.accounts["tester_bob"].interaction_count == 5


def test_diary_manager(tmp_path: Path) -> None:
    diary_mgr = DiaryManager(tmp_path)

    # Append first session
    diary_mgr.append_entry(
        mood="productive",
        what_i_did="Wrote unit test cases.",
        what_i_learned="FastAPI is awesome.",
        how_it_went="Perfect.",
        thoughts_for_next_time="Write integration test cases.",
        session_num=1,
        date_str="2026-06-18",
    )

    # Append second session (auto-increment)
    diary_mgr.append_entry(
        mood="relaxed",
        what_i_did="Refactored code.",
        what_i_learned="Ruff is fast.",
        how_it_went="Clean.",
        thoughts_for_next_time="Run mypy.",
        date_str="2026-06-18",
    )

    recent = diary_mgr.get_recent_entries(limit=1)
    assert len(recent) == 1
    assert recent[0]["date"] == "2026-06-18"
    content = recent[0]["content"]
    assert "## Session 1" in content
    assert "## Session 2" in content
    assert "**Mood:** productive" in content
    assert "**Mood:** relaxed" in content


def test_memory_manager(tmp_path: Path) -> None:
    memory_mgr = MemoryManager(tmp_path)

    # Append some memories
    memory_mgr.append_episodic(
        event="posted_tweet",
        content="Tweet about testing",
        importance=0.5,
    )
    memory_mgr.append_episodic(
        event="replied_tweet",
        content="Reply to @alice_dev",
        importance=0.9,  # High importance
    )
    memory_mgr.append_semantic(
        fact="@alice_dev builds cool stuff",
        source="profile",
        confidence=0.9,
        importance=0.8,  # High importance
    )
    memory_mgr.append_important(
        content="Write code daily",
        evidence="streak of 10 days",
        importance=1.0,  # High importance
    )

    # Test retrieval: min_importance = 0.8
    memories = memory_mgr.retrieve_memories(min_importance=0.8)

    # Total unique memories added = 4.
    # The low-importance episodic (importance=0.5) is kept because it's in the
    # recent episodic set (recency_limit defaults to 50, so we have all of them).
    assert len(memories) == 4

    # Test retrieval with high min_importance and no recency (set limit to 0)
    memories_filtered = memory_mgr.retrieve_memories(
        recency_limit=0, min_importance=0.8
    )
    assert len(memories_filtered) == 3  # The 3 memories with importance >= 0.8

    # Test query matching
    memories_query = memory_mgr.retrieve_memories(
        recency_limit=0, min_importance=0.95, mention_query="alice_dev"
    )
    # The matching ones:
    # 1. Reply to @alice_dev (importance=0.9)
    # 2. @alice_dev builds cool stuff (importance=0.8)
    # Both should be present because they mention "alice_dev", despite importance < 0.95
    # Plus "Write code daily" because its importance is 1.0 >= 0.95.
    assert len(memories_query) == 3
    contents = [
        m.get("content") or m.get("fact") or "" for m in memories_query
    ]
    assert any("Reply to @alice_dev" in c for c in contents)
    assert any("@alice_dev builds cool" in c for c in contents)

    # Test token budget capping
    # Let's write many mock memories to exceed budget
    for i in range(100):
        memory_mgr.append_episodic(
            event="mock_event",
            content=f"Mock memory payload number {i} to consume character space",
            importance=0.1 + (i * 0.005),  # range from 0.1 to 0.6
        )

    # Retrieve with small token budget (e.g. 50 tokens ~ 200 characters)
    memories_capped = memory_mgr.retrieve_memories(
        recency_limit=105, min_importance=0.0, token_budget=50
    )
    # It must return a small subset, and it must keep the highest importance memories
    assert len(memories_capped) < 100
    # The highest importance ones are the ones we added first
    # (e.g. Write code daily with 1.0)
    # Let's check that the highly important ones are prioritized
    capped_contents = [
        m.get("content") or m.get("fact") or "" for m in memories_capped
    ]
    assert "Write code daily" in capped_contents


def test_persona_with_target_kols(tmp_path: Path) -> None:
    # 1. Test persona with target_kols
    persona_data = {
        "id": "kol_hunter",
        "display_name": "KOL Hunter",
        "x_handle": "@kol_hunter",
        "identity": {
            "background": "AI and Tech commentator",
        },
        "personality": {
            "communication_style": "Sharp and insightful",
        },
        "interests": {},
        "writing_style": {
            "tone": "analytical",
            "typical_length": "medium",
        },
        "goals": {},
        "rules": {},
        "target_kols": [
            {
                "handle": "paulg",
                "category": "startups",
                "priority": "high",
                "preferred_angle": "framework",
            },
            {
                "handle": "sama",
                # category, priority, preferred_angle will use defaults
            },
        ],
    }
    persona_path = tmp_path / "persona.yaml"
    with persona_path.open("w", encoding="utf-8") as f:
        yaml.dump(persona_data, f)

    persona = load_persona(tmp_path)
    assert len(persona.target_kols) == 2
    
    kol1 = persona.target_kols[0]
    assert isinstance(kol1, TargetKOL)
    assert kol1.handle == "paulg"
    assert kol1.category == "startups"
    assert kol1.priority == "high"
    assert kol1.preferred_angle == "framework"

    kol2 = persona.target_kols[1]
    assert isinstance(kol2, TargetKOL)
    assert kol2.handle == "sama"
    assert kol2.category == "general"
    assert kol2.priority == "medium"
    assert kol2.preferred_angle == "insight"

    # 2. Test persona without target_kols (default to empty list)
    minimal_persona_data = {
        "id": "minimal",
        "display_name": "Minimal",
        "x_handle": "@minimal",
        "identity": {"background": "Minimal background"},
        "personality": {"communication_style": "Direct"},
        "interests": {},
        "writing_style": {"tone": "plain", "typical_length": "short"},
        "goals": {},
        "rules": {},
    }
    min_path = tmp_path / "min_persona"
    min_path.mkdir()
    with (min_path / "persona.yaml").open("w", encoding="utf-8") as f:
        yaml.dump(minimal_persona_data, f)

    min_persona = load_persona(min_path)
    assert min_persona.target_kols == []
