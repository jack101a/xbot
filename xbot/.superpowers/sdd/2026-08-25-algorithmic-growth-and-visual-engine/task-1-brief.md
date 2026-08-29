### Task 1: Algorithmic Opportunity & Growth Scorer

**Files:**
- Create: `backend/xbot/ai/growth_scorer.py`
- Test: `backend/tests/test_growth_scorer.py`

**Interfaces:**
- Produces: `score_tweet_opportunity(tweet_data: dict, author_history: dict | None = None) -> OpportunityScore`
  `calculate_engagement_velocity(impressions: int, likes: int, replies: int, created_at_utc: datetime) -> float`

**Requirements:**
1. Implement Pydantic model `OpportunityScore`:
   - `score: float` (0.0 to 100.0)
   - `reply_loop_multiplier: float` (up to 150.0x for active reply-back authors)
   - `bookmark_potential: float` (up to 50.0x for checklists/frameworks/data)
   - `velocity: float` (rate of engagements per hour)
   - `has_link_penalty: bool` (true if post contains external URL, applying 0.3x penalty)
   - `author_is_verified: bool` (applies 2.5x - 4.0x multiplier)
   - `recommended_action: str` ("sniper_reply", "quote_tweet", "bookmark_reference", "skip")
   - `reasoning: str`

2. Implement `calculate_engagement_velocity`:
   - Inputs: `impressions: int`, `likes: int`, `replies: int`, `created_at_utc: datetime`.
   - Age decay: half-life of 6 hours ($e^{-\lambda \Delta t}$ where $\lambda = \ln(2) / 6$).
   - Returns velocity score.

3. Implement `score_tweet_opportunity`:
   - Penalize tweets with external URLs (0.3x multiplier).
   - Penalize 0% reply authors / pure broadcast news bots.
   - Reward verified creators with high reply probability.
   - Detect bookmarkable content patterns (numbers, lists, code, "framework", "cheatsheet").

4. Test Suite `backend/tests/test_growth_scorer.py`:
   - Test verified active creator gets high score (>70).
   - Test tweet with external link gets penalized.
   - Test aged tweet (>12h) gets decayed score.
   - Test velocity calculation.
   - Test bookmark potential detection.

5. Test Command: `backend/.venv/bin/pytest backend/tests/test_growth_scorer.py -v`
