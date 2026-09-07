import pytest
from xbot.ai.formatting_engine import (
    PostFormattingArchetype,
    ARCHETYPE_REGISTRY,
    select_archetype,
    enforce_pacing_whitespace,
    strip_formulaic_trailing_emojis,
    enforce_length_cadence,
    post_process_formatted_content,
)


def test_archetype_registry_completeness():
    for archetype in PostFormattingArchetype:
        assert archetype in ARCHETYPE_REGISTRY
        spec = ARCHETYPE_REGISTRY[archetype]
        assert spec.min_chars > 0
        assert spec.max_chars >= spec.min_chars
        assert len(spec.few_shot_examples) >= 2
        assert spec.directives != ""


def test_select_archetype_media_bias():
    # When media is attached, MEDIA_SETUP_HOOK and MICRO_PUNCHLINE should dominate
    for _ in range(30):
        arch = select_archetype(topic="New camera sensor tested", has_media=True)
        assert arch in [
            PostFormattingArchetype.MEDIA_SETUP_HOOK,
            PostFormattingArchetype.MICRO_PUNCHLINE,
            PostFormattingArchetype.CONTRAST_BLOCKS,
        ]


def test_select_archetype_keyword_contrast():
    arch = select_archetype(topic="PostgreSQL vs MongoDB for high scale", has_media=False)
    assert arch in [
        PostFormattingArchetype.CONTRAST_BLOCKS,
        PostFormattingArchetype.HOT_TAKE_PUNCH,
        PostFormattingArchetype.STACCATO_OBSERVATION,
        PostFormattingArchetype.MICRO_PUNCHLINE,
        PostFormattingArchetype.MINI_LIST_FRAMEWORK,
        PostFormattingArchetype.SCENARIO_DIALOGUE,
        PostFormattingArchetype.DEBATE_DILEMMA,
    ]


def test_select_archetype_anti_monotony_cooldown():
    recent = [PostFormattingArchetype.MICRO_PUNCHLINE.value]
    # The immediate predecessor should have 0% chance of consecutive selection
    for _ in range(50):
        arch = select_archetype(topic="General tech update", has_media=False, recent_archetypes=recent)
        assert arch != PostFormattingArchetype.MICRO_PUNCHLINE


def test_enforce_pacing_whitespace():
    raw = "Heading line\n- Point 1\n- Point 2\n\n\n\nConcluding thought."
    formatted = enforce_pacing_whitespace(raw)
    assert "\n\n- Point 1" in formatted
    assert "\n\n\n" not in formatted
    assert "Concluding thought." in formatted


def test_strip_formulaic_trailing_emojis():
    text_with_dump = "The M4 Max efficiency is unmatched. 🚀🔥✨"
    stripped = strip_formulaic_trailing_emojis(text_with_dump, strip_probability=1.0)
    assert "🚀" not in stripped
    assert "🔥" not in stripped
    assert "✨" not in stripped
    assert stripped.endswith(".")


def test_preserve_clean_ending():
    clean_text = "Clean observation with no trailing emoji."
    res = strip_formulaic_trailing_emojis(clean_text, strip_probability=1.0)
    assert res == clean_text


def test_enforce_length_cadence_micro():
    long_text = "This is a very long text that exceeds the limit for a quick micro punchline test."
    res = enforce_length_cadence(long_text, archetype=PostFormattingArchetype.MICRO_PUNCHLINE, max_hard_limit=50)
    assert len(res) <= 50


def test_post_process_formatted_content_full_pipeline():
    raw = "Senior engineers:\nWriting code\n\nJunior engineers:\nThinking about code 🚀🔥"
    processed = post_process_formatted_content(raw, archetype=PostFormattingArchetype.CONTRAST_BLOCKS)
    assert "🚀" not in processed
    assert "\n\n" in processed
    assert len(processed) > 10
