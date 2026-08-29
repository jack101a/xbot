### Task 2: "Value-First + Debate Catalyst" Sniper Reply Upgrades

**Files:**
- Modify: `backend/xbot/ai/sniper.py`
- Test: `backend/tests/test_ai_sniper.py`

**Interfaces:**
- Consumes: `OpportunityScore` from `backend/xbot/ai/growth_scorer.py`
- Produces: `generate_sniper_reply(persona, target_tweet, preferred_angle) -> SniperResult`
  `SniperResult` with:
  - `reply_text: str` (strictly 140–260 chars, sentence case, ending with debate catalyst question)
  - `debate_catalyst: str` (the extracted closing question)
  - `angle: str` ("contrarian", "framework", "question", "witty", "data")
  - `reasoning: str`
  - `gif_query: str | None`

**Requirements:**
1. Upgrade `SNIPER_PROMPT_TEMPLATE` in `backend/xbot/ai/sniper.py`:
   - Enforce the 3-part formula:
     1. The Contrarian / Value Hook: Validate or challenge premise with insight, zero generic greetings.
     2. Concrete Proof / Data Angle: High-density takeaway or counter-intuitive mechanism.
     3. The Debate Catalyst: An open-ended question compelling the author to reply back ($+150\times$ multiplier).
   - Strict length constraint: between 140 and 260 characters.
   - Ban generic AI clichés ("delve", "testament", "tapestry", "supercharge", "Great post!").

2. Update `SniperResult` Pydantic model:
   - Add `debate_catalyst: str` field.
   - Add validator ensuring reply ends with a question mark (`?`).

3. Update `backend/tests/test_ai_sniper.py`:
   - Add tests asserting that generated replies contain the 3-part structure, end with `?`, and avoid boilerplate.
   - Verify all existing tests in `test_ai_sniper.py` continue to pass.

4. Test Command: `backend/.venv/bin/pytest backend/tests/test_ai_sniper.py -v`
