# Task 5 Brief: Browser Action Native GIF Search & File Upload Automation

## Objective
Enhance `ReplyToTweet` and `ComposePost` in `backend/xbot/browser/actions/x_actions.py` to reliably execute native Tenor / X GIF searches and selections:
1. When `gif_query` is provided in `ReplyToTweet.execute(page, reply_text=..., tweet_url=..., gif_query=...)` or `ComposePost.execute(page, text=..., gif_query=...)`:
   - Click GIF search button: `button[aria-label="Add a GIF"]`, `[data-testid="gifSearchButton"]`.
   - Wait for and type into GIF search input: `input[data-testid="searchBox"]` or `input[placeholder*="Search GIFs"]`.
   - Wait for GIF items to load: `[data-testid="gifItem"]` or `[data-testid="gifSearchResults"] img`.
   - Click the first or second matching GIF item.
   - Type accompanying text (if any) and submit.
   - Handle timeout or missing GIF gracefully by falling back to text-only posting without crashing.
2. Ensure `browser_queue.py` forwards `gif_query` and `media_paths` into `ReplyToTweet.execute`, `ComposePost.execute`, and `QuoteTweet.execute`.

## Files
- Modify: `backend/xbot/browser/actions/x_actions.py`
- Modify: `backend/xbot/pipelines/browser_queue.py`
- Test: `backend/tests/test_browser_queue.py` and `backend/tests/test_x_actions.py`

## Requirements & TDD Steps
1. Write/update unit tests in `backend/tests/test_browser_queue.py` and `backend/tests/test_x_actions.py` testing GIF search invocation, successful selection, and fallback resilience.
2. Implement GIF picker automation in `backend/xbot/browser/actions/x_actions.py`.
3. Run `backend/.venv/bin/pytest backend/tests/test_browser_queue.py backend/tests/test_x_actions.py -v`.
4. Run full browser action test suite.
5. Commit changes:
   `git add backend/xbot/browser/actions/x_actions.py backend/xbot/pipelines/browser_queue.py backend/tests/test_browser_queue.py backend/tests/test_x_actions.py`
   `git commit -m "feat(browser): implement native Tenor GIF search and selection in browser actions"`
6. Write report to `/home/ubuntu/projects/xbot/.superpowers/sdd/2026-08-27-natural-content-and-contextual-replies/task-5-report.md`.
