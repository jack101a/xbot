"""
Unit tests for xbot.contracts DTOs and Ports.
"""
import pytest
from xbot.contracts.browser import (
    BrowserActionType,
    BrowserRequest,
    BrowserResponse,
    ActionResult,
    TweetData,
    NotificationData,
    FollowListResult,
    ScrapeResult,
)
from xbot.contracts.ports import BrowserPort, LLMPort, GuardPort
from xbot.contracts.pipeline import PipelineResult


def test_browser_action_type_enum():
    assert BrowserActionType.LIKE == "like"
    assert BrowserActionType.REPLY == "reply"
    assert BrowserActionType.FOLLOW == "follow"
    assert BrowserActionType.POST == "post"
    assert BrowserActionType.SCRAPE_FEED == "scrape_feed"


def test_browser_request_defaults():
    req = BrowserRequest(
        profile_slug="test_profile",
        action=BrowserActionType.POST,
        params={"text": "Hello world from clean architecture!"}
    )
    assert req.profile_slug == "test_profile"
    assert req.action == BrowserActionType.POST
    assert req.timeout_seconds == 120
    assert req.idempotency_key is None
    assert req.params["text"] == "Hello world from clean architecture!"


def test_action_result_and_browser_response():
    act_res = ActionResult(
        status="success",
        detail="Tweet posted successfully",
        target_id="1234567890",
        url="https://x.com/test_profile/status/1234567890"
    )
    resp = BrowserResponse(
        status="success",
        action=BrowserActionType.POST,
        action_result=act_res
    )
    assert resp.status == "success"
    assert resp.action_result.target_id == "1234567890"
    assert resp.action_result.url == "https://x.com/test_profile/status/1234567890"
    assert resp.error is None


def test_scrape_result_normalization():
    tweets = [
        TweetData(
            tweet_id="999",
            url="https://x.com/author/status/999",
            handle="author",
            text="Autonomous AI is here",
            metrics={"likes": 100, "retweets": 25}
        )
    ]
    notifs = [
        NotificationData(
            kind="follow",
            actor_handle="fan123",
            text="fan123 followed you"
        )
    ]
    follow_list = FollowListResult(
        list_type="followers",
        handles=["fan123", "fan456"]
    )
    scrape = ScrapeResult(
        tweets=tweets,
        notifications=notifs,
        follow_list=follow_list
    )
    resp = BrowserResponse(
        status="success",
        action=BrowserActionType.SCRAPE_FEED,
        scrape=scrape
    )
    assert len(resp.scrape.tweets) == 1
    assert resp.scrape.tweets[0].handle == "author"
    assert resp.scrape.notifications[0].actor_handle == "fan123"
    assert resp.scrape.follow_list.handles == ["fan123", "fan456"]


def test_pipeline_result():
    res = PipelineResult(
        pipeline="follow_pipeline",
        status="success",
        actions_executed=5,
        per_profile={"test_profile": {"followed": 5}},
        duration_seconds=12.4
    )
    assert res.pipeline == "follow_pipeline"
    assert res.actions_executed == 5
    assert res.duration_seconds == 12.4
    assert res.errors == []


@pytest.mark.asyncio
async def test_mock_ports_implementation():
    class MockBrowser(BrowserPort):
        async def execute(self, request: BrowserRequest) -> BrowserResponse:
            return BrowserResponse(
                status="success",
                action=request.action,
                action_result=ActionResult(status="success", detail="Mocked execution")
            )

    class MockLLM(LLMPort):
        async def complete(self, prompt: str, *, model: str | None = None, temperature: float = 0.7, response_schema: dict | None = None) -> str:
            return "Mocked AI output"

        async def generate_image(self, prompt: str, **kwargs) -> bytes:
            return b"fake_png_bytes"

    class MockGuard(GuardPort):
        async def can_act(self, profile_slug: str, action: str, target_id: str | None = None) -> bool:
            return True

        async def record_action(self, profile_slug: str, action: str, target_id: str | None = None) -> None:
            pass

        async def record_failure(self, profile_slug: str, error: str) -> None:
            pass

    browser = MockBrowser()
    llm = MockLLM()
    guard = MockGuard()

    req = BrowserRequest(profile_slug="test_profile", action=BrowserActionType.LIKE, params={"tweet_id": "123"})
    resp = await browser.execute(req)
    assert resp.status == "success"
    assert resp.action_result.detail == "Mocked execution"

    completion = await llm.complete("Generate a hook")
    assert completion == "Mocked AI output"

    can_like = await guard.can_act("test_profile", "like")
    assert can_like is True
