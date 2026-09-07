# Natural Content Diversity & Context-Aware Reply Engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transform XBot from rigid, formulaic single-length text into a fully context-aware, human-authentic creation and reply engine with 6 dynamic reply modes (GIFs, emojis, one-liners, sarcasm, takes, deep breakdowns), room-reading top comments, and multi-format autonomous original content (4:5 vertical memes, threads with media, polls, hot takes).

**Architecture:** 
- Playwright scrapes root tweet text, image descriptions, and top 8–10 comments.
- LLM acts as an unconstrained room-reader, selecting 1 of 6 response modes without artificial length minimums or forced `?` endings.
- Formatting engine and anti-ai gatekeeper strip all outer quotation marks and preserve micro-reactions.
- Trend generator pipeline dynamically routes topics into 4:5 memes, media threads, polls, or hot takes based on depth.
- Browser queue executes native Tenor GIF search, media uploads, and atomic multi-tweet threads.

**Tech Stack:** Python 3.11, FastAPI, Celery, Playwright Async, SQLAlchemy (Async), Redis, Pydantic v2, Pytest.

**Spec:** [`docs/superpowers/specs/2026-08-27-natural-content-and-contextual-replies-design.md`](file:///home/ubuntu/projects/xbot/docs/superpowers/specs/2026-08-27-natural-content-and-contextual-replies-design.md)

## Global Constraints
- Zero outer surrounding quotes (`"..."`, `'...'`, `“...”`) on any generated post, reply, or thread.
- Zero forced trailing question marks (`?`) on replies unless organically asking a question.
- Dynamic reply length: allow 1-word reactions (`"real"`, `"💀"`), Tenor GIFs, dry one-liners, or multi-sentence breakdowns.
- Context injection: pass root text, media descriptions, and top ~10 comments into `generate_sniper_reply`.
- 100% test pass rate across `pytest backend/tests/ -v`.

---

### Task 1: Multi-Modal Target Context Scraper & Payload Builder

**Files:**
- Modify: `backend/xbot/browser/actions/x_actions.py:705-895`
- Test: `backend/tests/test_x_actions_context.py`

**Interfaces:**
- Produces: `scrape_target_tweet_context(page: Page, target_idx: int = 0) -> dict[str, Any]` returning `{"author": str, "text": str, "views": int, "likes": int, "replies": int, "top_comments": list[dict[str, Any]], "media_urls": list[str], "media_alts": list[str]}`.

- [ ] **Step 1: Write test for scrape_target_tweet_context**

```python
# backend/tests/test_x_actions_context.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from xbot.browser.actions.x_actions import ReplyToTweet


@pytest.mark.asyncio
async def test_scrape_target_tweet_context_extracts_comments_and_media():
    action = ReplyToTweet()
    mock_page = AsyncMock()

    mock_tweet_el = AsyncMock()
    mock_user_el = AsyncMock()
    mock_user_el.inner_text = AsyncMock(return_value="Kaya @kaya_builds")
    mock_text_el = AsyncMock()
    mock_text_el.inner_text = AsyncMock(return_value="Building AI agents with deterministic state.")

    mock_tweet_el.query_selector = AsyncMock(side_effect=lambda sel: (
        mock_user_el if "User-Name" in sel else
        mock_text_el if "tweetText" in sel or "tweet_text" in sel else None
    ))
    mock_tweet_el.query_selector_all = AsyncMock(return_value=[])

    mock_comment_el = AsyncMock()
    mock_c_user = AsyncMock()
    mock_c_user.inner_text = AsyncMock(return_value="Alex @alex_dev")
    mock_c_text = AsyncMock()
    mock_c_text.inner_text = AsyncMock(return_value="Deterministic state is the only way.")
    mock_c_like = AsyncMock()
    mock_c_like.get_attribute = AsyncMock(return_value="15 likes")
    mock_c_like.inner_text = AsyncMock(return_value="15")

    mock_comment_el.query_selector = AsyncMock(side_effect=lambda sel: (
        mock_c_user if "User-Name" in sel else
        mock_c_text if "tweetText" in sel else
        mock_c_like if "like" in sel else None
    ))

    mock_page.query_selector_all = AsyncMock(return_value=[mock_tweet_el, mock_comment_el])
    mock_page.evaluate = AsyncMock()

    ctx = await action.scrape_target_tweet_context(mock_page, target_idx=0)
    assert ctx["author"] == "kaya_builds"
    assert "Building AI agents" in ctx["text"]
    assert len(ctx["top_comments"]) == 1
    assert ctx["top_comments"][0]["author"] == "alex_dev"
    assert ctx["top_comments"][0]["text"] == "Deterministic state is the only way."
```

- [ ] **Step 2: Run test to verify it fails/passes**

Run: `backend/.venv/bin/pytest backend/tests/test_x_actions_context.py -v`

- [ ] **Step 3: Refine scrape_target_tweet_context in x_actions.py**

Ensure clean fallback parsing for media alt text, vision summary extraction, and sorting comments by popularity.

- [ ] **Step 4: Run test to verify it passes**

Run: `backend/.venv/bin/pytest backend/tests/test_x_actions_context.py -v`

- [ ] **Step 5: Commit**

```bash
git add backend/xbot/browser/actions/x_actions.py backend/tests/test_x_actions_context.py
git commit -m "feat(browser): enhance scrape_target_tweet_context with top comments and media descriptions"
```

---

### Task 2: AI Room-Reader & Dynamic Reply Generator with 6 Modalities

**Files:**
- Modify: `backend/xbot/ai/sniper.py`
- Test: `backend/tests/test_ai_sniper.py`

**Interfaces:**
- Consumes: Target tweet payload with `text`, `author`, `top_comments`, `media_alts`, `views`.
- Produces: `SniperResult` with `response_mode`, `reply_text`, `gif_query`, `reasoning`.

- [ ] **Step 1: Write test for all 6 response modes and removal of forced '?'**

```python
# In backend/tests/test_ai_sniper.py
@pytest.mark.asyncio
async def test_generate_sniper_reply_supports_dynamic_modes_without_forced_question():
    persona = Persona(
        display_name="Kaya",
        x_handle="kaya_builds",
        identity=Identity(background="AI engineer in Delhi"),
        personality=Personality(traits=["witty", "sharp"], communication_style="casual banter"),
        writing_style=WritingStyle(tone="authentic", formatting=[]),
    )

    # 1. Pure reaction / Short one-liner
    mock_client = AsyncMock()
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(
            message=MagicMock(
                content=json.dumps({
                    "response_mode": "punchy_one_liner",
                    "reply_text": "real and painfully true",
                    "gif_query": None,
                    "reasoning": "Matching sarcastic tone of top comments",
                })
            )
        )
    ]
    mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

    res = await generate_sniper_reply(
        persona=persona,
        target_tweet={
            "author": "swyx",
            "text": "Every founder at 2am writing bash scripts",
            "top_comments": [{"author": "dev1", "text": "so true 😭", "likes": 50}],
        },
        client=mock_client,
    )
    assert res.reply_text == "real and painfully true"
    assert not res.reply_text.endswith("?")
    assert res.response_mode == "punchy_one_liner"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `backend/.venv/bin/pytest backend/tests/test_ai_sniper.py -v`

- [ ] **Step 3: Update sniper.py prompt, schema, and validation**

- Add `response_mode` to `SniperResult`.
- Update `SNIPER_PROMPT_TEMPLATE` to instruct the model to choose between `pure_gif`, `emoji_reaction`, `punchy_one_liner`, `witty_sarcasm`, `casual_take`, `in_depth_breakdown`.
- In `_build_sniper_user_prompt`, format `top_comments` and `media_alts` into the prompt block.
- Remove forced `reply_text = reply_text.rstrip(".! ") + "?"` at lines 573 and 593.

- [ ] **Step 4: Run test to verify it passes**

Run: `backend/.venv/bin/pytest backend/tests/test_ai_sniper.py -v`

- [ ] **Step 5: Commit**

```bash
git add backend/xbot/ai/sniper.py backend/tests/test_ai_sniper.py
git commit -m "feat(ai): upgrade sniper reply generator with 6 dynamic modalities and room-reading context"
```

---

### Task 3: Context-Enriched Reply Pipeline & Feed/KOL Integration

**Files:**
- Modify: `backend/xbot/pipelines/reply_pipeline.py`
- Test: `backend/tests/test_reply_pipeline.py`

**Interfaces:**
- Consumes: `scrape_target_tweet_context` result.
- Dispatches: `BrowserJob(action_type="reply", params={"text": formatted_reply, "gif_query": gif_query, "tweet_url": tweet_url})`.

- [ ] **Step 1: Write unit test in test_reply_pipeline.py**

Verify that `execute_kol_sniper_replies` and `execute_feed_replies` pass full context to `generate_sniper_reply` and forward `gif_query` to `BrowserJob`.

- [ ] **Step 2: Run test to verify current behavior**

Run: `backend/.venv/bin/pytest backend/tests/test_reply_pipeline.py -v`

- [ ] **Step 3: Implement context enrichment in reply_pipeline.py**

- When inspecting KOL or feed tweets, if `tweet_url` exists, run `scrape_target_tweet_context` or pass scraped thread comments.
- Forward `sniper_res.gif_query` into `reply_job.params["gif_query"]`.

- [ ] **Step 4: Run test to verify it passes**

Run: `backend/.venv/bin/pytest backend/tests/test_reply_pipeline.py -v`

- [ ] **Step 5: Commit**

```bash
git add backend/xbot/pipelines/reply_pipeline.py backend/tests/test_reply_pipeline.py
git commit -m "feat(pipeline): connect enriched thread context and gif parameters in reply pipeline"
```

---

### Task 4: Dynamic Trend Generator (4:5 Memes, Media Threads, Polls, Hot Takes)

**Files:**
- Modify: `backend/xbot/pipelines/trend_generator_pipeline.py`
- Test: `backend/tests/test_trend_generator_pipeline.py`

**Interfaces:**
- Consumes: `ResearchedTopic` with `topic`, `category`, `scraped_posts`, `downloaded_media`.
- Produces: Staged `Content` with `ContentType.POST`, `ContentType.THREAD`, `ContentType.POLL`, or 4:5 visual meme spec.

- [ ] **Step 1: Write test for format decision matrix in test_trend_generator_pipeline.py**

Test routing into:
1. 4:5 vertical meme spec when visual/lifestyle topic.
2. Multi-tweet thread attaching downloaded viral media when deep topic (>=8 posts).
3. Community poll when debate topic.
4. Single punchy take.

- [ ] **Step 2: Run test to verify failure**

Run: `backend/.venv/bin/pytest backend/tests/test_trend_generator_pipeline.py -v`

- [ ] **Step 3: Implement dynamic format decision matrix in trend_generator_pipeline.py**

Implement the 4-way routing matrix using `VisualEngine`, `generate_thread`, `CreatePoll`, and `synthesize_creator_post`.

- [ ] **Step 4: Run test to verify it passes**

Run: `backend/.venv/bin/pytest backend/tests/test_trend_generator_pipeline.py -v`

- [ ] **Step 5: Commit**

```bash
git add backend/xbot/pipelines/trend_generator_pipeline.py backend/tests/test_trend_generator_pipeline.py
git commit -m "feat(pipeline): implement dynamic 4-way creation matrix in trend generator pipeline"
```

---

### Task 5: Browser Action Native GIF Search & File Upload Automation

**Files:**
- Modify: `backend/xbot/browser/actions/x_actions.py` (`ReplyToTweet`, `ComposePost`)
- Modify: `backend/xbot/pipelines/browser_queue.py`
- Test: `backend/tests/test_browser_queue.py`

**Interfaces:**
- Executes native X / Tenor GIF picker searching and clicking when `gif_query` is passed to `ReplyToTweet.execute` or `ComposePost.execute`.

- [ ] **Step 1: Write unit tests for GIF picker interactions**

In `backend/tests/test_browser_queue.py`, assert that `gif_query` is correctly passed and handled.

- [ ] **Step 2: Run test to verify**

Run: `backend/.venv/bin/pytest backend/tests/test_browser_queue.py -v`

- [ ] **Step 3: Implement GIF picker click/type/select flow in x_actions.py**

Implement `_attach_gif_if_requested(page, gif_query)` with resilient X selectors (`[data-testid="gifSearchButton"]`, `input[data-testid="searchBox"]`, `[data-testid="gifItem"]`).

- [ ] **Step 4: Run test to verify it passes**

Run: `backend/.venv/bin/pytest backend/tests/test_browser_queue.py -v`

- [ ] **Step 5: Commit**

```bash
git add backend/xbot/browser/actions/x_actions.py backend/xbot/pipelines/browser_queue.py backend/tests/test_browser_queue.py
git commit -m "feat(browser): implement native Tenor GIF search and selection in browser actions"
```

---

### Task 6: Full Integration Test & Daemon Verification

- [ ] **Step 1: Run full test suite across entire repository**
Run: `backend/.venv/bin/pytest backend/tests/ -v`
Expected: 100% passing (275+ tests).

- [ ] **Step 2: Restart live daemons and trigger live test runs**
- Restart FastAPI server on port 8200.
- Restart Celery worker & beat.
- Trigger `POST /pipelines/reply/trigger` and `POST /pipelines/trend_generator/trigger`.
- Verify execution logs.
