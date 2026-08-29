# Task 2 Brief: AI Room-Reader & Dynamic Reply Generator with 6 Modalities

## Objective
Upgrade `backend/xbot/ai/sniper.py` to act as an unconstrained, highly authentic AI room-reader supporting 6 distinct response modes:
1. `pure_gif`: Tenor / X search query + optional short reaction text (`"real"`, `"💀"`, `"no notes"`).
2. `emoji_reaction`: 1–2 authentic emojis (e.g. `💀`, `😭`, `🔥`, `🤌`) when the room is purely reactive.
3. `punchy_one_liner`: Short conversational punch (20–70 chars) like *"ok i agree"*, *"they are not gonna like this one"*.
4. `witty_sarcasm`: 1–2 sentences of dry humor or relatable banter matching the comments.
5. `casual_take`: Clear point of view without lecturing.
6. `in_depth_breakdown`: 2–4 sentences of technical nuance or domain analysis when the context calls for an explanation.

## Critical Rules
- **NO Forced Question Marks (`?`)**: Completely remove forced `.rstrip(".! ") + "?"` from sniper generation and fallbacks. Only ask a question if the AI chose to.
- **NO Fixed Length Minimums**: Allow natural short lengths (<30 chars for GIFs/emojis/one-liners).
- **Context Injection**: Format and pass `top_comments` (author + text + likes) and `media_alts` / image descriptions from target tweet into the prompt.
- **Quote Stripping**: Clean all leading/trailing quotes from `reply_text`.

## Files
- Modify: `backend/xbot/ai/sniper.py`
- Test: `backend/tests/test_ai_sniper.py`

## Schema
```python
class SniperResult(BaseModel):
    response_mode: str = Field(
        default="witty_sarcasm",
        description="Response mode: pure_gif, emoji_reaction, punchy_one_liner, witty_sarcasm, casual_take, in_depth_breakdown"
    )
    reply_text: str = Field(..., description="The drafted high-value reply text (natural length, sentence case)")
    debate_catalyst: str = Field(default="", description="Optional closing question or hook if asked")
    angle: str = Field(default="insight", description="The angle chosen: contrarian, framework, question, witty, data, or insight")
    angle_used: str | None = Field(default=None, description="Backwards compatibility alias for angle")
    gif_query: str | None = Field(default=None, description="Search term for Tenor/X GIF picker or None")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    reasoning: str = Field(default="", description="Brief explanation of the chosen response mode and angle")
```

## Requirements & TDD Steps
1. Update `backend/tests/test_ai_sniper.py` to assert:
   - All 6 response modes are parsed and valid.
   - Replies without `?` remain untouched and are NOT forced to end with `?`.
   - Short replies (<50 chars) and pure GIFs are accepted and not rejected.
   - `top_comments` and `media_alts` are formatted into user prompt.
2. Implement upgrades in `backend/xbot/ai/sniper.py`.
3. Run `backend/.venv/bin/pytest backend/tests/test_ai_sniper.py -v`.
4. Run full AI test suite: `backend/.venv/bin/pytest backend/tests/test_ai_sniper.py backend/tests/test_post_synthesizer.py backend/tests/test_hook_optimizer.py backend/tests/test_visual_engine.py -v`.
5. Commit:
   `git add backend/xbot/ai/sniper.py backend/tests/test_ai_sniper.py`
   `git commit -m "feat(ai): implement 6 dynamic reply modalities and room-reading context injection"`
6. Write report to `/home/ubuntu/projects/xbot/.superpowers/sdd/2026-08-27-natural-content-and-contextual-replies/task-2-report.md`.
