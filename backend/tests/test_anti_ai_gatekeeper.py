import pytest
from xbot.ai.anti_ai_gatekeeper import AntiAIGatekeeper


@pytest.fixture
def gatekeeper() -> AntiAIGatekeeper:
    return AntiAIGatekeeper()


def test_valid_human_creator_post(gatekeeper: AntiAIGatekeeper) -> None:
    text = (
        "Most developer tool benchmarks are pure marketing theater.\n\n"
        "If an agent runtime cannot maintain deterministic state across a 15-minute retry loop, "
        "zero-shot code generation is completely useless in production.\n\n"
        "Deterministic state beats clever prompting every single time."
    )
    result = gatekeeper.validate(text)
    assert result.is_valid is True
    assert len(result.errors) == 0


def test_rejects_lazy_lowercase_whatsapp_sludge(gatekeeper: AntiAIGatekeeper) -> None:
    text = "tbh the problem with ai agents is state management nobody talks about it but if your context drops you are cooked fr"
    result = gatekeeper.validate(text)
    assert result.is_valid is False
    assert any("lowercase" in err.lower() for err in result.errors)


def test_rejects_corporate_ai_buzzwords(gatekeeper: AntiAIGatekeeper) -> None:
    text = (
        "We need to supercharge developer workflows and delve into the tapestry of autonomous systems.\n\n"
        "This is a true game-changer for engineering teams."
    )
    result = gatekeeper.validate(text)
    assert result.is_valid is False
    assert any("buzzword" in err.lower() for err in result.errors)


def test_rejects_formulaic_linkedin_ctas(gatekeeper: AntiAIGatekeeper) -> None:
    text = (
        "Most founders fail because they build before validating.\n\n"
        "Let that sink in. Agree or disagree? Drop your thoughts below!"
    )
    result = gatekeeper.validate(text)
    assert result.is_valid is False
    assert any("template phrase" in err.lower() for err in result.errors)


def test_rejects_emoji_bullet_vomit(gatekeeper: AntiAIGatekeeper) -> None:
    text = (
        "Here is the modern engineering stack:\n\n"
        "🚀 FastAPI for async APIs\n"
        "💡 Redis for caching\n"
        "🔥 PostgreSQL for persistence"
    )
    result = gatekeeper.validate(text)
    assert result.is_valid is False
    assert any("emoji used as bullet" in err.lower() for err in result.errors)


def test_rejects_routine_beverage_filler(gatekeeper: AntiAIGatekeeper) -> None:
    text = "Nothing beats drinking chai while sitting on terraces on a lazy Sunday morning."
    result = gatekeeper.validate(text)
    assert result.is_valid is False
    assert any("routine/beverage filler" in err.lower() for err in result.errors)


def test_remediate_minor_issues(gatekeeper: AntiAIGatekeeper) -> None:
    text = "🚀 “Clean code” isn’t about rules — it’s about clarity."
    remediated = gatekeeper.remediate_minor_issues(text)
    assert "“" not in remediated
    assert "”" not in remediated
    assert "’" not in remediated
    assert "- " in remediated


def test_strip_surrounding_quotes() -> None:
    from xbot.ai.anti_ai_gatekeeper import strip_surrounding_quotes

    # Double quotes
    assert strip_surrounding_quotes('"Clean architecture beats fast hacks."') == "Clean architecture beats fast hacks."
    # Single quotes
    assert strip_surrounding_quotes("'Why do benchmarks lie?'") == "Why do benchmarks lie?"
    # Smart / curly quotes
    assert strip_surrounding_quotes('“Why do benchmarks lie?”') == "Why do benchmarks lie?"
    assert strip_surrounding_quotes('‘Why do benchmarks lie?’') == "Why do benchmarks lie?"
    # Nested outer quotes
    assert strip_surrounding_quotes('""Double wrapped tweet""') == "Double wrapped tweet"
    # Preserves inner quotes
    assert strip_surrounding_quotes('"Why they call it "serverless" makes no sense."') == 'Why they call it "serverless" makes no sense.'

