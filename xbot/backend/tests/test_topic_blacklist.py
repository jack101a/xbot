import pytest
from xbot.safety.topic_blacklist import TopicBlacklistFilter, topic_blacklist_filter
from xbot.persona.loader import Persona, Identity, Interests, Rules, Personality, WritingStyle, Goals


@pytest.fixture
def sample_tech_persona():
    return Persona(
        id="test_tech",
        display_name="Tech Creator",
        x_handle="@techcreator",
        identity=Identity(background="Tech reviewer", occupation="Engineer"),
        personality=Personality(traits=["witty", "analytical"], communication_style="sharp"),
        writing_style=WritingStyle(tone="conversational", typical_length="short"),
        goals=Goals(short_term=["grow audience"], content_pillars=["Tech"]),
        interests=Interests(
            primary=["Smartphones", "AI Tools", "Laptops"],
            will_not_discuss=[
                "Indian electoral politics, BJP, Congress, Modi, Rahul Gandhi",
                "Cryptocurrency scams and airdrops",
                "Religious debates",
            ],
        ),
        rules=Rules(
            never=["Discuss partisan elections", "Promote meme coins"],
        ),
    )


def test_clean_text_passes():
    text = "The new M4 MacBook Pro battery life is legitimately impressive."
    blocked, reason = topic_blacklist_filter.is_blocked(text)
    assert blocked is False
    assert reason is None


def test_politics_category_blocked(sample_tech_persona):
    text = "Big drama in the upcoming Lok Sabha election regarding new cabinet ministers."
    blocked, reason = topic_blacklist_filter.is_blocked(text, sample_tech_persona)
    assert blocked is True
    assert "politics" in reason.lower() or "election" in reason.lower()


def test_modi_rahul_explicit_keyword_blocked(sample_tech_persona):
    text = "Narendra Modi and Rahul Gandhi clash over new economic policies."
    blocked, reason = topic_blacklist_filter.is_blocked(text, sample_tech_persona)
    assert blocked is True


def test_crypto_scams_blocked(sample_tech_persona):
    text = "Check out this new 100x gem memecoin launching on Solana! Drop your wallet address."
    blocked, reason = topic_blacklist_filter.is_blocked(text, sample_tech_persona)
    assert blocked is True
    assert "crypto" in reason.lower() or "memecoin" in reason.lower() or "wallet" in reason.lower()


def test_custom_taboo_phrase_blocked():
    custom_filter = TopicBlacklistFilter(global_taboos=["Bollywood Gossip", "Tea routines"])
    text = "The latest Bollywood gossip around their divorce is wild."
    blocked, reason = custom_filter.is_blocked(text)
    assert blocked is True


def test_filter_safe_items(sample_tech_persona):
    items = [
        "iPhone 17 Pro camera sensor upgrade looks massive.",
        "BJP and Congress debate in the assembly today.",
        "Claude 3.7 Sonnet hybrid reasoning benchmarks are out.",
        "Join our crypto airdrop whitelist right now!",
    ]
    safe = topic_blacklist_filter.filter_safe_items(items, sample_tech_persona)
    assert len(safe) == 2
    assert "iPhone 17" in safe[0]
    assert "Claude 3.7" in safe[1]
