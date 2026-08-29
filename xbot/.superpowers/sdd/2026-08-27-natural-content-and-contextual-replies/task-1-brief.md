# Task 1 Brief: Multi-Modal Target Context Scraper & Payload Builder

## Objective
Enhance `scrape_target_tweet_context` in `backend/xbot/browser/actions/x_actions.py` to reliably extract:
1. Root Tweet text & author handle.
2. Root Tweet metrics (views/impressions, likes, replies, retweets).
3. Attached media images, video URLs, and image alt text descriptions.
4. Top 8–10 visible comments, extracting commenter author handle, comment text, and like counts, sorted by engagement.
5. Provide clean dictionary return matching the interface specification.

## Files
- Modify: `backend/xbot/browser/actions/x_actions.py` (around lines 705–895)
- Test: `backend/tests/test_x_actions_context.py`

## Interface Specification
```python
async def scrape_target_tweet_context(self, page: Page, target_idx: int = 0) -> dict[str, Any]:
    # returns:
    # {
    #     "author": str,
    #     "text": str,
    #     "views": int,
    #     "impressions": int,
    #     "likes": int,
    #     "replies": int,
    #     "retweets": int,
    #     "top_comments": list[dict[str, Any]],  # each: {"author": str, "text": str, "likes": int}
    #     "media_urls": list[str],
    #     "media_alts": list[str],
    # }
```

## Requirements & TDD Steps
1. Write `backend/tests/test_x_actions_context.py` testing:
   - Root tweet extraction (author, text, metrics).
   - Comments extraction with handles, text, and like counts.
   - Media alt text extraction.
   - Robustness when comments are missing or page structure is minimal.
2. Run pytest to confirm failures: `backend/.venv/bin/pytest backend/tests/test_x_actions_context.py -v`.
3. Refine `scrape_target_tweet_context` in `backend/xbot/browser/actions/x_actions.py`.
4. Run pytest to confirm passing: `backend/.venv/bin/pytest backend/tests/test_x_actions_context.py -v`.
5. Run core test suite: `backend/.venv/bin/pytest backend/tests/test_x_actions.py backend/tests/test_browser_queue.py -v`.
6. Commit changes:
   `git add backend/xbot/browser/actions/x_actions.py backend/tests/test_x_actions_context.py`
   `git commit -m "feat(browser): enhance scrape_target_tweet_context with top comments and media descriptions"`
7. Write report to `/home/ubuntu/projects/xbot/.superpowers/sdd/2026-08-27-natural-content-and-contextual-replies/task-1-report.md`.
