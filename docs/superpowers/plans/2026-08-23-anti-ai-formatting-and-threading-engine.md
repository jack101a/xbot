# Anti-AI Formatting, Visual Typography & Multi-Tweet Threading Engine

Upgrade XBot Pro's content synthesis, persona configuration, browser automation, and dashboard to eliminate both lazy unformatted chat (Extreme A) and robotic corporate LinkedIn slop (Extreme B). Implement native multi-tweet thread generation (`1/N` ... `N/N`), automated Playwright thread publishing, deterministic Anti-AI gatekeeper validation, and connected thread staging in the UI.

---

## User Review Required

> [!IMPORTANT]
> **Key Architecture Decisions:**
> 1. **Formatting Paradigm Shift**: Moving from single-block uncapitalized text to clean sentence-case typography with double line breaks (`\n\n`), asymmetric sentence burstiness, and clean bullet markers (`•` / `-`).
> 2. **Multi-Tweet Threads**: Introducing native multi-tweet threads (3–6 tweets) with the 3-Tier Viral Formula (Hook $\rightarrow$ Atomic Takeaways $\rightarrow$ Conversion Closer & CTA).
> 3. **Deterministic Anti-AI Gatekeeper**: Enforces sentence casing, punctuation health, bans emoji-bullet vomit (🚀 💡 🔥), and blocks formulaic AI clichés (*supercharge, unleash, delve, let that sink in, etc.*).

---

## Proposed Changes

### 1. Persona & Identity Realism Layer

#### [MODIFY] [`data/profiles/test_profile1/persona.yaml`](file:///home/ubuntu/projects/xbot/data/profiles/test_profile1/persona.yaml)
- Purge `conversational_lowercase_aesthetic` and all-lowercase examples.
- Replace with authentic, high-status sentence-cased examples with proper punctuation, double line breaks, and conversational Hinglish wit.
- Add explicit typography rules: sentence casing, micro-spacing (`\n\n`), no emoji bullets, burstiness.

#### [MODIFY] [`data/profiles/test_profile1/character_card.json`](file:///home/ubuntu/projects/xbot/data/profiles/test_profile1/character_card.json)
- Update character card message examples to use proper capitalization and clean formatting.

---

### 2. Anti-AI Typography & Gatekeeper System

#### [NEW] [`backend/xbot/ai/anti_ai_gatekeeper.py`](file:///home/ubuntu/projects/xbot/backend/xbot/ai/anti_ai_gatekeeper.py)
- Build `AntiAIGatekeeper` with multi-stage deterministic checks:
  1. **Casing & Punctuation Health**: Rejects all-lowercase lazy text and excessive shouting.
  2. **Banned AI Lexicon**: Blocks corporate buzzwords (*supercharge, unleash, harness, delve, elevate, revolutionize, tapestry, beacon, testament*).
  3. **Banned AI Openers & CTAs**: Blocks *let that sink in, read that again, agree or disagree, in today's fast-paced world*.
  4. **Emoji Bullet Gating**: Hard-bans lines starting with emojis as bullets.
  5. **Syntactic Burstiness Check**: Analyzes sentence length variation to eliminate flat robotic cadence.
  6. **Auto-Remediator**: Normalizes curly quotes and cleans spacing.

#### [MODIFY] [`backend/xbot/ai/assembler.py`](file:///home/ubuntu/projects/xbot/backend/xbot/ai/assembler.py) & [`backend/xbot/ai/planner.py`](file:///home/ubuntu/projects/xbot/backend/xbot/ai/planner.py)
- Embed `ANTI_AI_TYPOGRAPHY_DIRECTIVE` into system and planning prompts.
- Add support for `thread` action in `PlannedAction` and session planner.

---

### 3. Multi-Tweet Thread Engine

#### [NEW] [`backend/xbot/ai/thread_generator.py`](file:///home/ubuntu/projects/xbot/backend/xbot/ai/thread_generator.py)
- Generator for 3–6 tweet threads structured with:
  - **Tweet 1 (Hook)**: Contrarian premise, curiosity gap, or data proof (< 140 chars).
  - **Tweets 2 to N-1 (Body)**: 1 standalone takeaway per tweet with clean bullets (< 260 chars).
  - **Tweet N (Closer)**: TL;DR summary + bookmark/repost CTA + debate-sparking question.
- Integrated with `AntiAIGatekeeper` with automatic retry loop.

#### [MODIFY] [`backend/xbot/models/content.py`](file:///home/ubuntu/projects/xbot/backend/xbot/models/content.py)
- Add `ThreadItem` model (with `content_id`, `position`, `item_type`, `text`, `tweet_id`).
- Add `ContentType.THREAD` to `Content` model.

#### [MODIFY] [`backend/xbot/browser/actions/x_actions.py`](file:///home/ubuntu/projects/xbot/backend/xbot/browser/actions/x_actions.py)
- Add `ComposeThread` Playwright action:
  - Opens compose modal and types Tweet 1.
  - Clicks `addButton` (`+`) to add consecutive textareas.
  - Types subsequent tweets with human think pauses.
  - Submits atomically with `Post all` button and captures all created tweet IDs.

---

### 4. API Endpoints & Dashboard Staging

#### [MODIFY] [`backend/xbot/api/tools.py`](file:///home/ubuntu/projects/xbot/backend/xbot/api/tools.py) & [`backend/xbot/api/profiles.py`](file:///home/ubuntu/projects/xbot/backend/xbot/api/profiles.py)
- Add `POST /api/tools/generate-thread` endpoint.
- Add `POST /api/profiles/{id}/publish-thread` endpoint.
- Extend draft endpoints to retrieve and update multi-tweet thread items.

#### [MODIFY] [`dashboard/src/components/GrowthEngineTab.tsx`](file:///home/ubuntu/projects/xbot/dashboard/src/components/GrowthEngineTab.tsx) & [`dashboard/src/components/OverviewTab.tsx`](file:///home/ubuntu/projects/xbot/dashboard/src/components/OverviewTab.tsx)
- Add Thread Generator sub-tool tab to Growth Engine.
- Render thread drafts in Overview Tab with vertical connected spine lines, character counters, inline editing, and 1-click "Approve & Post Thread".

---

## Verification Plan

### Automated Tests
1. **Anti-AI Gatekeeper Tests**:
   - `backend/.venv/bin/pytest backend/tests/test_anti_ai_gatekeeper.py`
   - Test rejection of lowercase chat, corporate buzzwords, emoji bullets, and flat sentence cadence.
2. **Thread Generator & Integration Tests**:
   - `backend/.venv/bin/pytest backend/tests/test_thread_generator.py`
   - Test thread creation, character limits (< 280), and schema validation.
3. **Full Backend Test Suite**:
   - `backend/.venv/bin/pytest backend/tests/` (ensure 100% pass across all 150+ tests).

### Manual & End-to-End Verification
1. Run end-to-end script `test-script/verify_anti_ai_and_threads.py` testing live synthesis and gatekeeper validation.
2. Build Next.js frontend (`npm run build` in `dashboard/`) and verify zero errors.
