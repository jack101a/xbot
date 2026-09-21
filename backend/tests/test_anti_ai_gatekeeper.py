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


def test_rejects_persona_boundary_violations(gatekeeper: AntiAIGatekeeper) -> None:
    from pathlib import Path
    from xbot.persona.loader import load_persona

    profile_dir = Path(__file__).resolve().parents[2] / "data" / "profiles" / "test_profile1"
    persona = load_persona(profile_dir)

    # Violation 1: Claiming ownership of forbidden item (e.g. dedicated GPUs / MacBooks)
    gpu_tweet = "Just spun up my new dedicated GPU cluster and my RTX 4090 is running at 100% load."
    res1 = gatekeeper.validate(gpu_tweet, persona=persona)
    assert res1.is_valid is False
    assert any("never_owns" in err for err in res1.errors)

    # Violation 2: Claiming to be a software engineer / developer
    dev_tweet = "As a software engineer and compiler dev, I optimize memory models every single day."
    res2 = gatekeeper.validate(dev_tweet, persona=persona)
    assert res2.is_valid is False
    assert any("never_claim_to_be" in err for err in res2.errors)

    # Valid human reaction (spectator / creator perspective)
    valid_tweet = "Honestly, the wild part about these new local models is seeing everyone run them on phones instead of waiting for cloud APIs."
    res3 = gatekeeper.validate(valid_tweet, persona=persona)
    assert res3.is_valid is True


def test_rejects_gibberish_and_token_math_leaks(gatekeeper: AntiAIGatekeeper) -> None:
    # Exact reproduction of the user's reported gibberish action
    gibberish = "-t-'-s (5) + ' ' + c-o-n-n-e-c-t (7) + '.' (1) = 43\n\n#500Followers"
    res1 = gatekeeper.validate(gibberish)
    assert res1.is_valid is False
    assert any("arithmetic" in err or "calculation" in err for err in res1.errors)

    # Calculation leak
    calc_leak = "Here is the equation: x + y = 43"
    res2 = gatekeeper.validate(calc_leak)
    assert res2.is_valid is False

    # Chain of thought tag leak
    cot_leak = "<think>\nLet me count the characters\n</think>\nHere is a tweet"
    res3 = gatekeeper.validate(cot_leak)
    assert res3.is_valid is False


def test_growth_post_is_gibberish_or_leak() -> None:
    from xbot.ai.growth_post_generator import is_gibberish_or_leak

    assert is_gibberish_or_leak("-t-'-s (5) + ' ' + c-o-n-n-e-c-t (7) + '.' (1) = 43") is True
    assert is_gibberish_or_leak("x + y = 43") is True
    assert is_gibberish_or_leak("<think>scratchpad</think>") is True
    assert is_gibberish_or_leak("Short") is True  # under 10 chars
    assert is_gibberish_or_leak("{'tweet_copy': 'hello'}") is True  # raw json leak

    # Valid human tweet
    assert is_gibberish_or_leak("Looking for active mutuals on X! Drop your handle below and let's connect.") is False


