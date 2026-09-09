# Task: Dynamic Character Reality & Boundaries Architecture

## Objective
Implement dynamic character boundaries (`owns`, `never_owns`, `expert_in`, `spectator_only`, `never_claim_to_be`) in backend models and dashboard UI, and create a single centralized `build_character_master_prompt` that prepends to every prompt at the top across all generation pipelines (posts, replies, quotes, polls, visual posts).

## Phases
- [x] 1. **Design Gate**: Author `DESIGN.md` conforming to project design tokens.
- [x] 2. **Backend Models & Persona**:
   - Updated `backend/xbot/persona/models.py` with `ProfileBoundaries`.
   - Updated `data/profiles/test_profile1/persona.yaml` with Kaya's curated boundary values.
- [x] 3. **Master Character Prompt Engine**:
   - Created `backend/xbot/persona/prompt_engine.py` with `build_character_master_prompt()`.
   - Wired to all 5 generation engines:
     - `post_synthesis_builder.py` / `post_synthesizer.py`
     - `sniper/prompt_builder.py`
     - `sniper/quote_generator.py`
     - `poll_prompts.py`
     - `visual_inference.py`
- [x] 4. **Purge Coder / GPU Few-Shots & Gatekeeper Safety**:
   - Cleaned `backend/xbot/ai/formatting/typography.py` and `prompt_builder.py` (purged M4 Max, Safari CSS, GPU sweating few-shots).
   - Added Gatekeeper 0 boundary violation checks to `AntiAIGatekeeper` catching claims of `never_owns` and `never_claim_to_be`.
- [x] 5. **Dashboard UI**:
   - Added `boundaries` to `dashboard/src/features/persona/types.ts`.
   - Added `BoundariesEditor.tsx` in `dashboard/src/features/persona/components/`.
   - Integrated "Reality & Boundaries" sub-tab into `PersonaMemoryTab.tsx`.
   - Compiled Next.js static production export (`npm run build` succeeded).
- [x] 6. **Verification & Deployment**:
   - Verified `scripts/diagnostics/verify_master_character_prompt.py` passes all assertions.
   - Verified Gatekeeper tests (`test_anti_ai_gatekeeper.py`) pass 100%.
   - Verified live REST API persistence of boundaries via PUT/GET on port 8300.
   - Restarted local backend, Celery workers, and dashboard via `./xbot.sh restart`.
