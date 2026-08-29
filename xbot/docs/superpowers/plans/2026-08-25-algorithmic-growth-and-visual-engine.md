# Modern X Algorithmic Growth & Visual Engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the mathematical scoring, 4:5 visual/meme generation, debate catalyst sniper replies, and bookmark-bait hook optimizations based on the modern X (Twitter) algorithm research (Phoenix / Grok Recommender).

**Architecture:** 
1. `growth_scorer.py`: Computes compound Phoenix objective scores ($+150\times$ author reply loop, $+50\times$ bookmarks, $+20\times$ dwell, $-80\%$ link penalty) and filters low-signal targets.
2. `sniper.py`: Upgrades reply synthesis to follow the 3-stage "Value Hook $\to$ Data Angle $\to$ Debate Catalyst" architecture to maximize author reply-back probability.
3. `visual_engine.py`: Generates "One-Two Punch" setups and 4:5 portrait image prompts with high-contrast dark-mode typography.
4. `hook_optimizer.py` & `post_synthesizer.py`: Enforces $<100$ char cliffhangers for "Show more" expansion and generates bookmark-bait cheat sheets.
5. `tasks.py`: Implements the 1st-reply link injection bypass and integrates the full growth scoring loop.

**Tech Stack:** Python 3.11, FastAPI, Pydantic v2, SQLAlchemy (asyncio), Playwright, Pytest.

**Spec:** Synthesized research from X Algorithm (Phoenix Transformer & Home Mixer), Multi-Modal Vision Embeddings (CLIP/Grok Vision), and 2025/2026 Impression Multiplier hierarchy.

## Global Constraints

- Preserve all existing unit tests in `backend/tests/`.
- No external links allowed in the main post body (must be routed to 1st reply or bio).
- All visual prompts must specify 4:5 portrait (`1080x1350`) or 1:1 square aspect ratios.
- Replies must be strictly between 140 and 260 characters and end with an engaging debate question.
- Clean sentence case, zero generic AI boilerplate ("delve", "testament", "tapestry", "supercharge").

---

### Task 1: Algorithmic Opportunity & Growth Scorer

**Files:**
- Create: `backend/xbot/ai/growth_scorer.py`
- Test: `backend/tests/test_growth_scorer.py`

**Interfaces:**
- Produces: `score_tweet_opportunity(tweet_data: dict, author_history: dict | None) -> OpportunityScore`
  `calculate_engagement_velocity(impressions: int, likes: int, replies: int, created_at_utc: datetime) -> float`

- [ ] **Step 1: Write the failing test**
Create `backend/tests/test_growth_scorer.py` with tests for:
1. High score for recent blue-tick tweets with high author reply probability ($+150\times$).
2. Penalty and low score for tweets with external links ($-70\%$).
3. Score decay over time ($e^{-\lambda \Delta t}$ with 6h half-life).
4. Velocity scoring calculation.

- [ ] **Step 2: Run test to verify it fails**
Run: `backend/.venv/bin/pytest backend/tests/test_growth_scorer.py -v`
Expected: FAIL with ModuleNotFoundError or import error.

- [ ] **Step 3: Write minimal implementation in `backend/xbot/ai/growth_scorer.py`**
Implement Pydantic model `OpportunityScore(score: float, reply_loop_multiplier: float, bookmark_potential: float, velocity: float, recommended_action: str)` and calculation functions.

- [ ] **Step 4: Run test to verify it passes**
Run: `backend/.venv/bin/pytest backend/tests/test_growth_scorer.py -v`
Expected: PASS (4/4 tests).

- [ ] **Step 5: Commit**
`git add backend/xbot/ai/growth_scorer.py backend/tests/test_growth_scorer.py && git commit -m "feat(ai): implement algorithmic opportunity and growth scorer based on Phoenix weights"`

---

### Task 2: "Value-First + Debate Catalyst" Sniper Reply Upgrades

**Files:**
- Modify: `backend/xbot/ai/sniper.py:200-350`
- Test: `backend/tests/test_ai_sniper.py`

**Interfaces:**
- Consumes: `OpportunityScore` from `growth_scorer.py`
- Produces: `generate_sniper_reply(persona, target_tweet, preferred_angle) -> SniperResult` with `debate_catalyst_question`, `angle`, `reply_text` strictly $\in [140, 260]$ chars.

- [ ] **Step 1: Write/update the failing test**
Update `backend/tests/test_ai_sniper.py` to assert that generated sniper replies:
1. Follow the 3-part structure (Value Hook $\to$ Concrete Angle $\to$ Debate Catalyst).
2. End with an open-ended question mark (`?`) to drive author reply loops.
3. Contain no banned boilerplate words ("Great post", "Totally agree", "supercharge", "delve").

- [ ] **Step 2: Run test to verify it fails**
Run: `backend/.venv/bin/pytest backend/tests/test_ai_sniper.py -k "test_debate_catalyst_structure" -v`
Expected: FAIL.

- [ ] **Step 3: Implement prompt upgrades in `backend/xbot/ai/sniper.py`**
Add the Debate Catalyst instructions and Pydantic validation schema ensuring length between 140–260 chars and presence of closing debate catalyst.

- [ ] **Step 4: Run test to verify it passes**
Run: `backend/.venv/bin/pytest backend/tests/test_ai_sniper.py -v`
Expected: PASS (all tests).

- [ ] **Step 5: Commit**
`git add backend/xbot/ai/sniper.py backend/tests/test_ai_sniper.py && git commit -m "feat(ai): upgrade sniper replies with 3-stage Value Hook and Debate Catalyst architecture"`

---

### Task 3: Visual & 4:5 Meme Engine

**Files:**
- Create: `backend/xbot/ai/visual_engine.py`
- Test: `backend/tests/test_visual_engine.py`

**Interfaces:**
- Produces: `generate_visual_post_spec(topic: str, format_type: str, persona: Persona) -> VisualPostSpec`
  `VisualPostSpec(tweet_copy: str, image_prompt: str, aspect_ratio: str, color_palette: str, target_simcluster: str)`

- [ ] **Step 1: Write the failing test**
Create `backend/tests/test_visual_engine.py` testing:
1. `generate_visual_post_spec` returns valid `VisualPostSpec` with aspect ratio `"4:5"` or `"1:1"`.
2. `tweet_copy` is $<140$ characters acting as tension/setup hook.
3. `image_prompt` contains high-contrast, photorealistic/dark-mode specifications without AI artifacts.

- [ ] **Step 2: Run test to verify it fails**
Run: `backend/.venv/bin/pytest backend/tests/test_visual_engine.py -v`
Expected: FAIL with ModuleNotFoundError.

- [ ] **Step 3: Implement `backend/xbot/ai/visual_engine.py`**
Implement the visual engine supporting 4 pillars (Creator Reality, Cinema Buff, Tech/AI Irony, Community Debates), "One-Two Punch" caption separation, and 4:5 aspect ratio specifications.

- [ ] **Step 4: Run test to verify it passes**
Run: `backend/.venv/bin/pytest backend/tests/test_visual_engine.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**
`git add backend/xbot/ai/visual_engine.py backend/tests/test_visual_engine.py && git commit -m "feat(ai): implement 4:5 visual and meme engine with One-Two Punch captioning"`

---

### Task 4: Bookmark-Bait & Open-Loop Hook Optimizer

**Files:**
- Modify: `backend/xbot/ai/hook_optimizer.py:10-120`
- Modify: `backend/xbot/ai/post_synthesizer.py:50-200`
- Test: `backend/tests/test_hook_optimizer.py`, `backend/tests/test_post_synthesizer.py`

**Interfaces:**
- Produces: `optimize_post_for_virality(draft: str, goal: str) -> OptimizedPostResult` with `open_loop_hook` ($<100$ chars), `bookmark_score` (1-10), `clean_body` (link-free), and `extracted_link` (if any).

- [ ] **Step 1: Write the failing tests**
Add test asserting that `post_synthesizer.py` strips raw links from the post body, preserves an open-loop cliffhanger before the 140-char fold, and produces numbered high-utility bookmark frameworks.

- [ ] **Step 2: Run tests to verify they fail**
Run: `backend/.venv/bin/pytest backend/tests/test_post_synthesizer.py -k "test_open_loop_and_link_extraction" -v`
Expected: FAIL.

- [ ] **Step 3: Implement open-loop & bookmark-bait upgrades**
Update `hook_optimizer.py` and `post_synthesizer.py` to enforce the $<100$ char curiosity cliffhanger and link extraction for 1st-reply placement.

- [ ] **Step 4: Run tests to verify they pass**
Run: `backend/.venv/bin/pytest backend/tests/test_hook_optimizer.py backend/tests/test_post_synthesizer.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**
`git add backend/xbot/ai/hook_optimizer.py backend/xbot/ai/post_synthesizer.py backend/tests/test_post_synthesizer.py && git commit -m "feat(ai): add open-loop cliffhangers and bookmark-bait framework synthesis"`

---

### Task 5: 1st-Reply Link Injection & Execution Loop Integration

**Files:**
- Modify: `backend/xbot/tasks.py:650-850`
- Test: `backend/tests/test_link_injection_and_pipeline.py`

**Interfaces:**
- Consumes: `VisualPostSpec`, `OpportunityScore`, `generate_sniper_reply`, `post_synthesizer`
- Produces: Seamless session execution in `_run_session_async` with link-in-reply staging and growth scoring.

- [ ] **Step 1: Write integration test**
Create `backend/tests/test_link_injection_and_pipeline.py` validating that when a post has an external link, it is queued for 1st-reply injection rather than embedded in the main tweet.

- [ ] **Step 2: Run test to verify it fails**
Run: `backend/.venv/bin/pytest backend/tests/test_link_injection_and_pipeline.py -v`
Expected: FAIL.

- [ ] **Step 3: Implement 1st-reply link injection in `tasks.py`**
In `tasks.py` post publishing handler: if `extracted_link` exists, schedule or immediately post a follow-up reply containing the clean link reference after posting the main tweet.

- [ ] **Step 4: Run all test suites to verify full green pass**
Run: `backend/.venv/bin/pytest backend/tests/ -v`
Expected: All tests PASS.

- [ ] **Step 5: Commit**
`git add backend/xbot/tasks.py backend/tests/test_link_injection_and_pipeline.py && git commit -m "feat(pipeline): implement 1st-reply link injection and algorithmic growth execution loop"`
