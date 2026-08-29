# Task 3 Brief: Context-Enriched Reply Pipeline & Feed/KOL Integration

## Objective
Update `backend/xbot/pipelines/reply_pipeline.py` to:
1. Extract full target thread context (root text, media descriptions, top 10 comments with likes, and metrics) using `scrape_target_tweet_context` or the check payload.
2. Pass the enriched context dictionary into `generate_sniper_reply(persona=persona, target_tweet=target_dict, opportunity_score=opp_score)`.
3. Extract `sniper_res.gif_query` and pass it to `BrowserJob(action_type="reply", params={"tweet_id": tweet_id, "tweet_url": tweet_url, "text": formatted_reply, "gif_query": sniper_res.gif_query})`.
4. Ensure `execute_kol_sniper_replies`, `execute_fast_response_replies`, and `execute_feed_replies` all support dynamic response modes (including short reactions like `"real"`, `"💀"`, pure GIFs, or multi-sentence breakdowns).

## Files
- Modify: `backend/xbot/pipelines/reply_pipeline.py`
- Test: `backend/tests/test_reply_pipeline.py`

## Requirements & TDD Steps
1. Update `backend/tests/test_reply_pipeline.py` to test:
   - Enriched thread context with top comments and media descriptions is forwarded into sniper generator.
   - `gif_query` is passed through into `BrowserJob.params`.
   - Short reactions and non-question replies execute successfully and record in database without errors.
2. Implement updates in `backend/xbot/pipelines/reply_pipeline.py`.
3. Run `backend/.venv/bin/pytest backend/tests/test_reply_pipeline.py -v`.
4. Run core pipeline test suite: `backend/.venv/bin/pytest backend/tests/test_reply_pipeline.py backend/tests/test_like_pipeline.py backend/tests/test_quote_pipeline.py backend/tests/test_follow_pipeline.py backend/tests/test_browser_queue.py -v`.
5. Commit changes:
   `git add backend/xbot/pipelines/reply_pipeline.py backend/tests/test_reply_pipeline.py`
   `git commit -m "feat(pipeline): wire enriched thread context and gif parameters in reply pipeline"`
6. Write report to `/home/ubuntu/projects/xbot/.superpowers/sdd/2026-08-27-natural-content-and-contextual-replies/task-3-report.md`.
