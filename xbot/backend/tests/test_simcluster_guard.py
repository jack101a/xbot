import pytest
from xbot.safety.simcluster_guard import (
    CANONICAL_PROFILES,
    SimClusterTopicScorer,
    enforce_natural_entity_density,
)


def test_enforce_natural_entity_density():
    # 0 max hashtags -> all hashtags converted to plain words
    text_multiple = "Testing our new #vLLM deployment with #PyTorch and #Kubernetes in production."
    cleaned = enforce_natural_entity_density(text_multiple, max_hashtags=1)
    # Only 1 hashtag preserved (the last one), earlier ones converted to words
    assert "#Kubernetes" in cleaned
    assert "#vLLM" not in cleaned
    assert "vLLM" in cleaned
    assert "#PyTorch" not in cleaned
    assert "PyTorch" in cleaned

    # Single hashtag remains untouched when max_hashtags=1
    text_single = "Check out the new update on #TechTwitter"
    assert enforce_natural_entity_density(text_single, max_hashtags=1) == text_single


def test_simcluster_topic_scorer_delhi_aligned():
    profile = CANONICAL_PROFILES["delhi_lifestyle"]
    scorer = SimClusterTopicScorer(profile)

    aligned_text = "Hauz Khas Social on a Friday evening is basically LinkedIn in real life. Swiggy One delivering at 2 AM is the only reliable thing."
    res = scorer.validate_content(aligned_text, content_type="post")

    assert res.is_aligned is True
    assert res.recommended_action == "approve"
    assert len(res.detected_violations) == 0
    assert res.primary_similarity > 0.0


def test_simcluster_topic_scorer_anti_anchor_violation():
    profile = CANONICAL_PROFILES["delhi_lifestyle"]
    scorer = SimClusterTopicScorer(profile)

    # Post contains CUDA and vLLM which dilute Delhi lifestyle into AI Infra
    unaligned_text = "Optimizing my CUDA kernels with vLLM token throughput benchmarks."
    res = scorer.validate_content(unaligned_text, content_type="post")

    assert res.is_aligned is False
    assert res.recommended_action == "regenerate"
    assert any("Forbidden cross-niche entity" in v for v in res.detected_violations)
    assert res.remediation_prompt is not None
    assert "Delhi Urban Lifestyle" in res.remediation_prompt


def test_simcluster_topic_scorer_hashtag_limit():
    profile = CANONICAL_PROFILES["ai_infra"]
    scorer = SimClusterTopicScorer(profile)

    excessive_tags = "Benchmarking token throughput with #AI #LLM #Infra #MachineLearning"
    res = scorer.validate_content(excessive_tags, content_type="post")

    assert res.is_aligned is False
    assert any("Hashtag spam detected" in v for v in res.detected_violations)


def test_simcluster_topic_scorer_tech_aligned():
    profile = CANONICAL_PROFILES["ai_infra"]
    scorer = SimClusterTopicScorer(profile)

    aligned_text = "Benchmarking vLLM token throughput against ONNX Runtime for local model deployments."
    res = scorer.validate_content(aligned_text, content_type="post")

    assert res.is_aligned is True
    assert res.recommended_action == "approve"
