### Task 4: Bookmark-Bait & Open-Loop Hook Optimizer

**Files:**
- Modify: `backend/xbot/ai/hook_optimizer.py`
- Modify: `backend/xbot/ai/post_synthesizer.py`
- Test: `backend/tests/test_hook_optimizer.py`, `backend/tests/test_post_synthesizer.py`

**Interfaces:**
- Produces: `optimize_post_for_virality(draft: str, goal: str = "bookmark_and_dwell") -> OptimizedPostResult`
  `OptimizedPostResult` Pydantic model:
  - `open_loop_hook: str` (Curiosity cliffhanger strictly $<100$ characters before the fold)
  - `bookmark_score: float` (1.0 to 10.0)
  - `clean_body: str` (Link-free formatted body with numbered framework/bullet points)
  - `extracted_link: str | None` (Isolated external URL for 1st-reply injection)
  - `archetype: str` ("contrarian_reversal", "asymmetric_result", "zero_to_hero", "framework_breakdown")
  - `full_optimized_text: str`

**Requirements:**
1. Upgrade `backend/xbot/ai/hook_optimizer.py`:
   - Add open-loop cliffhanger generator targeting the first 100 characters before the fold ("Show more").
   - Add bookmark-bait framework evaluator (detecting numbered action steps, swipe files, cheat sheets).
   - Strip external links from `clean_body` and isolate them in `extracted_link`.

2. Upgrade `backend/xbot/ai/post_synthesizer.py`:
   - Enforce link extraction so standalone creator posts are 100% native text/media.
   - Inject the $<100$ char cliffhanger hook into generated post formats.

3. Update test suites:
   - `backend/tests/test_hook_optimizer.py`: test open-loop hook length $<100$ chars, bookmark score calculation, and link stripping.
   - `backend/tests/test_post_synthesizer.py`: test link extraction and clean post formatting.

4. Test Command: `backend/.venv/bin/pytest backend/tests/test_hook_optimizer.py backend/tests/test_post_synthesizer.py -v`
