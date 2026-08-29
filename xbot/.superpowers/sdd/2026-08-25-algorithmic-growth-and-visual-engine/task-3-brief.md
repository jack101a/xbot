### Task 3: Visual & 4:5 Meme Engine

**Files:**
- Create: `backend/xbot/ai/visual_engine.py`
- Test: `backend/tests/test_visual_engine.py`

**Interfaces:**
- Produces: `generate_visual_post_spec(topic: str, format_type: str | None = None, persona: Persona | None = None) -> VisualPostSpec`
  `VisualPostSpec` Pydantic model:
  - `tweet_copy: str` (Setup tension hook $<140$ chars)
  - `image_prompt: str` (Detailed prompt specifying 4:5 portrait aspect ratio, lighting, dark mode, high contrast)
  - `aspect_ratio: str` ("4:5" or "1:1")
  - `format_type: str` ("storyboard_4panel", "side_by_side", "urban_lifestyle", "dark_infographic")
  - `target_simcluster: str` ("Tech/AI", "Cinema/Prestige", "Urban/Creator", "Anime/PopCulture")
  - `one_two_punch_strategy: str`

**Requirements:**
1. Implement `backend/xbot/ai/visual_engine.py`:
   - "One-Two Punch" separation: Tweet copy acts as the tension hook; image delivers visual punchline.
   - Default aspect ratio: `4:5` portrait (`1080x1350`) for mobile screen takeover (~74% viewport).
   - High-contrast dark-mode theme (`#0D1117`) for infographics/cheat sheets.
   - Persona-tailored aesthetic templates (Kaya's urban South Asian creator realism, raw 35mm film photography, 4-panel grids, minimalist tech terminal).

2. Implement `generate_visual_post_spec` with AI routing fallback (Gemini Flash / DeepSeek).

3. Create test suite `backend/tests/test_visual_engine.py`:
   - Test generating a 4:5 visual post spec for each of the 4 pillars.
   - Test tweet copy length is strictly $<140$ characters.
   - Test aspect ratio defaults to 4:5.

4. Test Command: `backend/.venv/bin/pytest backend/tests/test_visual_engine.py -v`
