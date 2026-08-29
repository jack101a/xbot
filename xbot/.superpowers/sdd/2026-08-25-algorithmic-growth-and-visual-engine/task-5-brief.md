### Task 5: 1st-Reply Link Injection & Execution Loop Integration

**Files:**
- Modify: `backend/xbot/tasks.py`
- Test: `backend/tests/test_link_injection_and_pipeline.py`

**Interfaces:**
- Consumes: `growth_scorer.score_tweet_opportunity`, `visual_engine.generate_visual_post_spec`, `hook_optimizer.optimize_post_for_virality`, `sniper.generate_sniper_reply`
- Produces: Resilient autonomous pipeline execution with 1st-reply link injection.

**Requirements:**
1. In `backend/xbot/tasks.py`:
   - In `p_action.type == "post"` execution:
     - Check if post metadata or `Content` record contains an `extracted_link`.
     - When publishing the post via `ComposePost` or staging it, if an `extracted_link` is present, record a follow-up action or immediately publish the first reply containing: `"Link / source breakdown: {extracted_link}"` after publishing the main post.
   - Integrate `score_tweet_opportunity` into target tweet ranking before sniper replies or quotes are executed.
   - When opportunity score recommends `"skip"`, gracefully bypass the target and record reason.

2. Create test suite `backend/tests/test_link_injection_and_pipeline.py`:
   - Test that posts with links extract the URL cleanly and stage/publish a 1st reply.
   - Test growth scorer integration with session planner action decisions.

3. Test Command: `backend/.venv/bin/pytest backend/tests/test_link_injection_and_pipeline.py -v`
