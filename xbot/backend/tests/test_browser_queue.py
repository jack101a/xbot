import json
import time
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from xbot.pipelines.browser_queue import (
    BrowserJob,
    enqueue_browser_job,
    execute_browser_action,
    get_browser_job_result,
    get_queue_depth,
    pop_next_job,
    process_single_job,
    set_browser_job_result,
)


def test_enqueue_and_pop_priority():
    mock_redis = MagicMock()
    mock_redis.zcard.return_value = 1

    # Simulate pop
    job = BrowserJob(
        action_type="like",
        profile_slug="test_slug",
        params={"tweet_id": "123"},
        priority=0,
        job_id="job-abc",
    )
    mock_redis.zpopmin.return_value = [("job-abc", 0.0)]
    mock_redis.get.return_value = json.dumps({
        "action_type": "like",
        "profile_slug": "test_slug",
        "params": {"tweet_id": "123"},
        "priority": 0,
        "job_id": "job-abc",
        "created_at": time.time(),
        "ttl_seconds": 300,
    })

    job_id = enqueue_browser_job(job, r=mock_redis)
    assert job_id == "job-abc"
    mock_redis.set.assert_called_once()
    mock_redis.zadd.assert_called_once()

    popped = pop_next_job(r=mock_redis)
    assert popped is not None
    assert popped.job_id == "job-abc"
    assert popped.action_type == "like"


def test_result_get_and_set():
    mock_redis = MagicMock()
    mock_redis.get.return_value = json.dumps({"status": "success", "tweet_id": "123"})

    set_browser_job_result("job-123", {"status": "success", "tweet_id": "123"}, r=mock_redis)
    mock_redis.set.assert_called_with("xbot:browser_result:job-123", json.dumps({"status": "success", "tweet_id": "123"}), ex=600)

    res = get_browser_job_result("job-123", timeout_seconds=0, r=mock_redis)
    assert res == {"status": "success", "tweet_id": "123"}


@pytest.mark.asyncio
async def test_execute_browser_action_routing():
    mock_page = AsyncMock()

    with patch("xbot.pipelines.browser_queue.LikeTweet") as MockLike:
        mock_instance = MagicMock()
        mock_instance.execute = AsyncMock(return_value={"status": "liked"})
        MockLike.return_value = mock_instance

        res = await execute_browser_action(mock_page, "like", {"tweet_id": "123"})
        assert res == {"status": "liked"}
        mock_instance.execute.assert_called_once_with(mock_page, tweet_url=None)

    with patch("xbot.pipelines.browser_queue.ReplyToTweet") as MockReply:
        mock_instance = MagicMock()
        mock_instance.execute = AsyncMock(return_value={"status": "replied"})
        MockReply.return_value = mock_instance

        res = await execute_browser_action(
            mock_page,
            "reply",
            {
                "tweet_url": "https://x.com/user/status/123",
                "text": "nice",
                "gif_query": "celebrate",
                "media_paths": ["/tmp/image.png"],
            },
        )
        assert res == {"status": "replied"}
        mock_instance.execute.assert_called_once_with(
            mock_page,
            reply_text="nice",
            tweet_url="https://x.com/user/status/123",
            tweet_index=None,
            gif_query="celebrate",
            media_paths=["/tmp/image.png"],
        )

    with patch("xbot.pipelines.browser_queue.QuoteTweet") as MockQuote:
        mock_instance = MagicMock()
        mock_instance.execute = AsyncMock(return_value={"status": "quoted"})
        MockQuote.return_value = mock_instance

        res = await execute_browser_action(
            mock_page,
            "quote",
            {
                "tweet_url": "https://x.com/user/status/456",
                "text": "Check this out",
                "gif_query": "mind blown",
                "media_paths": ["/tmp/quote.jpg"],
            },
        )
        assert res == {"status": "quoted"}
        mock_instance.execute.assert_called_once_with(
            mock_page,
            quote_text="Check this out",
            tweet_url="https://x.com/user/status/456",
            tweet_index=None,
            gif_query="mind blown",
            media_paths=["/tmp/quote.jpg"],
        )

    with patch("xbot.pipelines.browser_queue.ComposePost") as MockPost:
        mock_instance = MagicMock()
        mock_instance.execute = AsyncMock(return_value={"status": "posted"})
        MockPost.return_value = mock_instance

        res = await execute_browser_action(
            mock_page,
            "post",
            {
                "text": "Hello world",
                "gif_query": "party",
                "media_paths": ["/tmp/photo.png"],
            },
        )
        assert res == {"status": "posted"}
        mock_instance.execute.assert_called_once_with(
            mock_page,
            text="Hello world",
            media_paths=["/tmp/photo.png"],
            gif_query="party",
        )



@pytest.mark.asyncio
async def test_process_single_job_expired():
    mock_redis = MagicMock()
    mock_manager = MagicMock()

    expired_job = BrowserJob(
        action_type="like",
        profile_slug="test_slug",
        created_at=time.time() - 400,  # Expired
        ttl_seconds=300,
    )

    res = await process_single_job(expired_job, mock_manager, mock_redis)
    assert res["status"] == "expired"
    mock_manager.get_context.assert_not_called()
