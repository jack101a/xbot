# Design Specification: KOL Sniper Reply & Fast Engagement Subsystem

**Date:** 2026-08-18  
**Status:** APPROVED  
**Author:** Antigravity Engineering  
**System:** XBot Social Agent Automation  

---

## 1. Executive Summary & Objective

The **KOL Sniper Reply Subsystem** enables XBot profiles to monitor a curated list of high-authority accounts (KOLs - Key Opinion Leaders) in real-time, detect new posts within seconds, generate high-insight context-aligned replies via LLM, and execute human-like browser replies within a 60–180 second window.

By securing top positions on high-traffic threads, XBot profiles exploit the **9.0x algorithm multiplier for replies** and siphon thousands of organic impressions, profile visits, and followers without paid API fees.

---

## 2. Architecture & Data Flow

```
┌────────────────────────────────────────────────────────┐
│               1. Celery Beat Scheduler                 │
│  Triggers `sniper_check_targets` periodic task (1-3m)  │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│            2. Profile Target KOL Selector              │
│  Fetches active profiles & their target_kols config    │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│         3. Playwright Stealth Profile Scanner          │
│  Navigates to x.com/<kol> & extracts latest tweet ID   │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│             4. Redis Deduplication Check               │
│  Key: `xbot:seen_tweets:<profile_slug>:<tweet_id>`     │
│  - If exists or tweet age > 20 mins: SKIP              │
│  - If new: Cache with TTL (7 days) & proceed           │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│             5. AI Sniper Response Engine               │
│  Evaluates tweet against persona identity, selects     │
│  angle (Contrarian / Framework / Witty / Data),        │
│  and generates concise, high-retention reply text.     │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│          6. Playwright Reply Execution & Log           │
│  Executes ReplyToTweet with human typing cadence.      │
│  Records Action(type=REPLY, metadata={"sniper": True}) │
└────────────────────────────────────────────────────────┘
```

---

## 3. Detailed Component Specifications

### 3.1 Persona Configuration Extension (`persona.yaml` / `loader.py`)
Add a `target_kols` schema to `Persona`:
```yaml
target_kols:
  - handle: "elonmusk"
    category: "tech_ai"
    priority: "high"
    preferred_angle: "witty_insight"
  - handle: "ylecun"
    category: "ai_research"
    priority: "high"
    preferred_angle: "contrarian_debate"
  - handle: "sama"
    category: "ai_industry"
    priority: "medium"
    preferred_angle: "framework_summary"
```

### 3.2 Browser Extraction Action (`xbot/browser/actions/x_actions.py`)
New action class `CheckUserLatestTweet`:
- **Inputs**: `handle: str`, `max_age_minutes: int = 15`
- **Behavior**: Navigates to `https://x.com/{handle}`, waits for the top tweet selector `[data-testid="tweet"]`, extracts the tweet ID, text content, relative timestamp, and replies count.
- **Output**: Structured dictionary `{"tweet_id": str, "text": str, "url": str, "created_at": str, "is_pinned": bool}`.

### 3.3 Sniper Angle & Response Engine (`xbot/ai/sniper.py`)
Generates high-value replies engineered for the X ranking algorithm:
- **Angles Supported**:
  1. `contrarian`: Respectfully challenges the core premise with a crisp, logical counter-example.
  2. `framework`: Distills the tweet into a 3-bullet actionable framework.
  3. `witty`: Delivers an insider observation or relatable punchline in character.
  4. `data`: Supplies a relevant data point or historical parallel.
- **Algorithm Constraints**:
  - No generic filler ("Great tweet!", "Totally agree!").
  - Under 240 characters for immediate readability without truncation.
  - Concludes with an intriguing micro-hook that invites responses.

### 3.4 Rate Limiting & Safety Integration (`xbot/safety/limiter.py`)
- Sniper replies consume standard `ActionType.REPLY` budget in the Redis sliding window.
- If the hourly or daily reply budget is below threshold (< 2 remaining), sniper tasks gracefully back off to preserve account safety.

### 3.5 Periodic Task Runner (`xbot/tasks.py`)
- Task `sniper_check_targets`: Celery task executing every 2 minutes with randomized jitter.
- Iterates over active profiles, picks the highest-priority KOLs whose last check exceeds the cooldown interval, and executes the sniper pipeline.

---

## 4. Error Handling & Edge Cases
1. **Target Account Suspended / Private**: Log warning, flag KOL in Redis cache for 24h backoff, continue to next target.
2. **Rate Limit Exhausted**: Soft skip without raising exceptions.
3. **Selector Changes / CAPTCHA**: Trigger standard `CircuitBreaker` and emit webhook alerts if CAPTCHA or lockout is detected.

---

## 5. Verification & Testing Plan
- **Unit Tests**:
  - Schema validation for `target_kols` in `PersonaLoader`.
  - Sniper prompt generation and angle selection in `xbot.ai.sniper`.
- **Integration Tests**:
  - `test_sniper_actions.py`: Validating tweet extraction against `mock_x_server`.
  - End-to-end task execution verifying Redis deduplication and Action logging.
