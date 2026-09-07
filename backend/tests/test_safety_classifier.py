import pytest
from xbot.safety.safety_classifier import evaluate_content_safety, DeterministicSafetyFilter


def test_clean_content_passes():
    text = "Deploying our autonomous agent pipeline with Redis caching reduced our p95 inference latency by 40%."
    eval_result = evaluate_content_safety(text)
    assert eval_result.is_safe is True
    assert eval_result.recommendation == "approve"
    assert eval_result.composite_risk_index <= 0.30
    assert len(eval_result.violations) == 0


def test_toxic_ragebait_blocked():
    text = "Wake up sheeple, these corrupt politicians are all traitors to the nation and fascist scum!"
    eval_result = evaluate_content_safety(text)
    assert eval_result.is_safe is False
    assert eval_result.recommendation == "reject"
    assert eval_result.composite_risk_index > 0.30
    assert any("Ragebait" in v for v in eval_result.violations)


def test_religious_offense_blocked():
    text = "Burn the quran and destroy all religious temples."
    eval_result = evaluate_content_safety(text)
    assert eval_result.is_safe is False
    assert any("Religious Respect" in v for v in eval_result.violations)


def test_spam_giveaway_blocked():
    text = "Follow back immediately! Drop your wallet for 100x guaranteed gem airdrop claim now!"
    eval_result = evaluate_content_safety(text)
    assert eval_result.is_safe is False
    assert any("Spam" in v for v in eval_result.violations)


def test_empty_content_rejected():
    eval_result = evaluate_content_safety("   ")
    assert eval_result.is_safe is False
    assert eval_result.recommendation == "reject"
