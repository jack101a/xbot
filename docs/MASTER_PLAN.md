# XBot — Master Implementation Plan

> **Version:** 1.0 · **Date:** 2026-06-18 · **Status:** IN PROGRESS
>
> A private, self-hosted X (Twitter) automation system that operates multiple
> profiles as fully-realized AI characters — browsing feeds, posting, engaging,
> growing audiences, and driving monetization — all through browser automation
> powered by LLM intelligence.

---

## Table of Contents

1. [Product Vision & Workflow](#1-product-vision--workflow)
2. [System Architecture](#2-system-architecture)
3. [Technology Stack](#3-technology-stack)
4. [Browser Automation Engine](#4-browser-automation-engine)
5. [AI Decision System](#5-ai-decision-system)
6. [Profile Persona & Diary System](#6-profile-persona--diary-system)
7. [Database Design](#7-database-design)
8. [Scheduling & Orchestration](#8-scheduling--orchestration)
9. [Rate Limits & Safety](#9-rate-limits--safety)
10. [Analytics & Strategy Engine](#10-analytics--strategy-engine)
11. [Admin Dashboard](#11-admin-dashboard)
12. [Docker & Portainer Deployment](#12-docker--portainer-deployment)
13. [Security & Secrets](#13-security--secrets)
14. [Logging & Observability](#14-logging--observability)
15. [Testing Strategy](#15-testing-strategy)
16. [Development Phases & Backlog](#16-development-phases--backlog)

---

## 1. Product Vision & Workflow

### 1.1 What the System Does

XBot is an autonomous agent system that manages one or more X (Twitter) accounts.
Each account is bound to a **persona** — a fully-described AI character with a
unique personality, knowledge base, writing style, goals, memories, and diary.

The system:

1. **Wakes up** on a human-like schedule (or is triggered manually).
2. **Loads the persona's full context** — character sheet, diary, recent memories,
   relationship graph, performance analytics, and current strategy.
3. **Asks the AI**: "Given who you are and what you know, what should you do right
   now?" The AI returns a prioritized action plan.
4. **Executes the plan** through browser automation — browsing the feed, composing
   posts, liking content, replying, following interesting accounts, engaging in
   conversations.
5. **Records what happened** — updates the diary, stores new memories, logs
   engagement data, notes new relationships.
6. **Evaluates performance** — the analytics engine scores how well the session
   went and feeds results back into the persona's strategy for next time.

### 1.2 Core Product Loop

```
┌─────────────────────────────────────────────────────────┐
│                    ORCHESTRATOR                         │
│  Schedule triggers ──► Pick next profile ──► Check     │
│  rate budget ──► Acquire browser lock                  │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│                  CONTEXT ASSEMBLY                       │
│  Load persona ──► Load diary (last 7 days) ──► Load    │
│  memories ──► Load relationships ──► Load analytics    │
│  ──► Load current strategy ──► Load feed snapshot      │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│                 AI DECISION ENGINE                      │
│  Send full context to LLM via LiteLLM ──► Receive     │
│  structured action plan (JSON) ──► Validate actions    │
│  against rate budget ──► Approve/trim plan             │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│               BROWSER AUTOMATION ENGINE                 │
│  Open persistent session ──► Execute actions one by    │
│  one with human-like delays ──► Capture results ──►   │
│  Handle errors/captchas ──► Screenshot on failure      │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│               POST-SESSION PROCESSING                   │
│  Update diary ──► Store new memories ──► Update        │
│  relationships ──► Record analytics ──► Adjust         │
│  strategy ──► Release browser lock                     │
└─────────────────────────────────────────────────────────┘
```

### 1.3 Monetization Path

| Milestone | Requirement | System Goal |
|:---|:---|:---|
| Build Audience | Consistent, high-quality posting | AI-generated original content aligned to persona |
| Grow Engagement | Reply threads, conversations, likes | AI reads feed, identifies opportunities, engages authentically |
| Hit 500 Followers | Organic growth through engagement | Track follower count, adjust strategy |
| Hit 5M Impressions/3mo | Viral content + consistent volume | Analytics-driven content optimization |
| Enable Ads Revenue | X Premium + Stripe connected | Manual step; system tracks eligibility progress |
| Creator Subscriptions | 2,000+ followers + 5M impressions | Premium exclusive content generation |
| Optimize Revenue | Maximize impressions from Premium users | Target engagement with verified/premium accounts |

---

## 2. System Architecture

### 2.1 High-Level Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                        DOCKER HOST (Portainer-managed)           │
│                                                                  │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────────────┐  │
│  │  Dashboard   │  │  FastAPI      │  │  LiteLLM Proxy         │  │
│  │  (Next.js)   │◄─┤  API Server   │──┤  (OpenAI-compat)       │  │
│  │  :3000       │  │  :8000        │  │  :4000                 │  │
│  └─────────────┘  └──────┬───────┘  └────────────────────────┘  │
│                          │                                       │
│                    ┌─────┴─────┐                                 │
│                    │           │                                  │
│               ┌────▼───┐  ┌───▼────────┐                        │
│               │ Redis  │  │ PostgreSQL │                         │
│               │ :6379  │  │ :5432      │                         │
│               └────────┘  └────────────┘                         │
│                    │                                             │
│  ┌─────────────────▼─────────────────────────────────────────┐  │
│  │                   WORKER CONTAINER                         │  │
│  │                                                            │  │
│  │  ┌─────────────┐  ┌──────────────┐  ┌─────────────────┐  │  │
│  │  │ Scheduler   │  │ Task Queue   │  │ Browser Pool    │  │  │
│  │  │ (Celery     │  │ (Celery      │  │ (Playwright     │  │  │
│  │  │  Beat)      │  │  Workers)    │  │  Persistent     │  │  │
│  │  │             │  │              │  │  Contexts)      │  │  │
│  │  └─────────────┘  └──────────────┘  └─────────────────┘  │  │
│  │                                                            │  │
│  │  ┌────────────────────────────────────────────────────┐   │  │
│  │  │              PERSONA DATA VOLUME                    │   │  │
│  │  │  /data/profiles/{profile_id}/                       │   │  │
│  │  │    ├── persona.yaml        (character definition)   │   │  │
│  │  │    ├── diary/              (daily diary entries)     │   │  │
│  │  │    ├── memories/           (episodic memories)       │   │  │
│  │  │    ├── relationships/      (known accounts)          │   │  │
│  │  │    ├── strategy.yaml       (current strategy)        │   │  │
│  │  │    └── browser_data/       (Playwright user data)    │   │  │
│  │  └────────────────────────────────────────────────────┘   │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

### 2.2 Service Responsibilities

| Service | Responsibility |
|:---|:---|
| **FastAPI API Server** | REST API for dashboard, profile CRUD, manual triggers, config, analytics queries |
| **Celery Worker** | Executes browser automation tasks, AI calls, post-session processing |
| **Celery Beat** | Triggers scheduled sessions per profile based on configured schedule |
| **Playwright Browser Pool** | Manages persistent browser contexts, one per profile, with stealth patches |
| **PostgreSQL** | Stores profiles, action logs, analytics, task history, rate limit state |
| **Redis** | Celery broker, rate limit counters (sliding window), session locks, caching |
| **LiteLLM Proxy** | Unified AI gateway — routes to any configured LLM provider |
| **Next.js Dashboard** | Admin UI for profile management, monitoring, analytics, manual overrides |

### 2.3 Key Architecture Decisions

| Decision | Choice | Rationale |
|:---|:---|:---|
| Language | Python 3.12+ | Best ecosystem for Playwright, Celery, FastAPI, LLM libraries |
| Browser engine | Playwright (Chromium) | Best stealth support, persistent contexts, async-native |
| Task queue | Celery + Redis | Battle-tested distributed task execution with scheduling |
| Database | PostgreSQL | Relational integrity for analytics; JSONB for flexible data |
| Persona storage | Hybrid (YAML files + DB cache) | YAML is human-readable/editable; DB caches computed state |
| AI gateway | LiteLLM Proxy (Docker) | Provider-agnostic; hot-swap models without code changes |
| Dashboard | Next.js + shadcn/ui | Modern, responsive, lightweight; REST via FastAPI |
| Deployment | Docker Compose + Portainer | Single-command deployment; Portainer for management UI |

---

## 3. Technology Stack

### 3.1 Backend

| Component | Technology | Notes |
|:---|:---|:---|
| Runtime | Python 3.12+ | Use `uv` for package management |
| Web framework | FastAPI | Async-first, auto-generated OpenAPI docs |
| Task queue | Celery 5.x | Redis broker |
| Scheduler | Celery Beat | Periodic + dynamic per-profile schedules |
| Browser automation | Playwright for Python | Async API, Chromium only |
| Stealth | playwright-stealth (patched) | + custom fingerprint patches as needed |
| ORM | SQLAlchemy 2.0 (async) | Alembic for migrations |
| Validation | Pydantic v2 | Request/response models, persona schema validation |
| AI client | OpenAI Python SDK | Pointed at LiteLLM proxy `base_url` |
| YAML parsing | ruamel.yaml | Preserves comments for human-editable persona files |
| Encryption | cryptography (Fernet) | For credential encryption at rest |

### 3.2 Frontend (Dashboard)

| Component | Technology |
|:---|:---|
| Framework | Next.js 15+ (App Router) |
| UI components | shadcn/ui + Radix primitives |
| Styling | Tailwind CSS 4 |
| Charts | Recharts |
| Server state | TanStack Query |
| Real-time | WebSocket (native, via FastAPI) |
| Auth | Simple bearer token (internal use) |

### 3.3 Infrastructure

| Component | Technology |
|:---|:---|
| Containers | Docker + Docker Compose |
| Management UI | Portainer CE |
| Database | PostgreSQL 16 |
| Cache / Broker | Redis 7 |
| AI Gateway | LiteLLM Proxy (Docker image) |
| Reverse proxy | Caddy (optional, for HTTPS if exposed) |

---

## 4. Browser Automation Engine

### 4.1 Design Principles

1. **One persistent browser context per profile** — never share sessions.
2. **Human-like timing** in every interaction — no machine-speed clicks.
3. **Stealth-first** — every browser launch applies anti-detection patches.
4. **Failure-tolerant** — every action wrapped in retry logic with screenshots on failure.
5. **Observable** — every browser action is logged with timing and outcome.

### 4.2 Browser Manager

The `BrowserManager` class is the core of browser automation. Responsibilities:

- Launch or reuse a persistent Playwright context per profile
- Apply stealth patches (navigator.webdriver, plugins, UA, canvas noise)
- Configure viewport, locale, timezone per profile config
- Save and restore cookies and localStorage automatically
- Provide page instances with pre-configured settings
- Handle graceful shutdown and session persistence to disk
- Enforce a single-context-per-profile lock via Redis

Each profile's browser data lives at `/data/profiles/{id}/browser_data/` and is
mounted as a Docker volume so state persists across container restarts.

### 4.3 Stealth Configuration

Each browser context must configure these to avoid detection:

| Setting | Strategy |
|:---|:---|
| **User-Agent** | Realistic, consistent per profile. Only rotate on major browser version bumps. |
| **Viewport** | Realistic resolution (1920×1080, 1440×900, etc.), consistent per profile |
| **Timezone** | Match the proxy's geographic region |
| **Locale** | Match timezone (e.g., `en-US` for US proxy) |
| **navigator.webdriver** | Patched to `undefined` via stealth plugin |
| **WebGL renderer** | Spoofed to match a real GPU for the claimed platform |
| **Canvas fingerprint** | Slight noise injection to avoid unique-canvas detection |
| **TLS fingerprint** | Use real Chromium build (not headless-specific JA3/JA4) |
| **Plugins & mimeTypes** | Inject realistic plugin list matching a real Chrome install |

### 4.4 Action Library

Every X interaction is encapsulated as an **Action** class with built-in human
simulation. Each action inherits from `BaseAction` which provides timing, error
handling, and logging automatically.

| Action | Human-Like Behavior |
|:---|:---|
| `BrowseFeed` | Scroll gradually (200-500px increments), pause 2-8s per tweet, occasional back-scroll |
| `ReadTweet` | Click into tweet, wait 3-12s (proportional to text length), scroll replies |
| `ComposePost` | Click compose, wait 1-3s, type char-by-char (50-120ms per char with typo simulation), pause before posting |
| `LikeTweet` | Wait 1-4s after reading, click like, wait 0.5-2s |
| `ReplyToTweet` | Read original (3-8s), click reply, type naturally, review (2-5s), post |
| `Retweet` | Wait 1-3s, click retweet, confirm |
| `QuoteTweet` | Click quote, type commentary naturally, review, post |
| `FollowUser` | Visit profile, browse 2-3 tweets (5-15s), then follow |
| `SearchQuery` | Click search, type query naturally, browse results |
| `VisitProfile` | Click through to profile, scroll through recent tweets |

### 4.5 Timing Engine

All delays use **bounded randomness** — never perfectly uniform, never absurdly long.

```
BaseDelay  = configured per action type (e.g., 3000ms for a like)
Jitter     = random(-30%, +50%) of BaseDelay
ThinkTime  = random(1000ms, 5000ms) — added before "decision" actions
TypeSpeed  = random(50ms, 120ms) per character
TypoChance = 5% per character → type wrong char, pause, backspace, retype

FinalDelay = BaseDelay + Jitter + ThinkTime (when applicable)
```

Between-action delays follow a **weighted random distribution** — most gaps are
2-8 seconds, but occasionally 15-30 seconds (simulating reading or distraction).

### 4.6 Error Handling & Recovery

| Error Type | Response |
|:---|:---|
| **Element not found** | Retry 3× with increasing wait (1s, 3s, 5s), then screenshot + skip |
| **Navigation timeout** | Reload page, retry once, then abort session |
| **Rate limit (429)** | Stop all actions, log event, exponential backoff (min 5 minutes) |
| **CAPTCHA detected** | Screenshot, log, pause session, notify via dashboard alert |
| **Login required** | Attempt session restore from cookies; if fail → flag for manual login |
| **Account locked/suspended** | Immediately stop, flag profile as `LOCKED`, admin notification |
| **Network error** | Retry with 30s backoff, max 3 retries, then abort |
| **Unknown DOM change** | Screenshot, log detailed element info, skip action, continue session |

### 4.7 Session Lifecycle

```
1. ACQUIRE LOCK     → Redis lock per profile (prevents concurrent sessions)
2. LAUNCH BROWSER   → Load persistent context from /data/profiles/{id}/browser_data/
3. APPLY STEALTH    → Inject stealth patches, verify fingerprint consistency
4. VERIFY SESSION   → Check if logged in (look for home feed elements)
5. EXECUTE ACTIONS  → Run AI-planned actions sequentially with timing
6. CAPTURE RESULTS  → Record outcomes (tweet IDs, engagement counts, errors)
7. SAVE STATE       → Persist cookies, localStorage, session data to disk
8. RELEASE LOCK     → Release Redis lock
9. LOG SESSION      → Write session summary to database
```

---

## 5. AI Decision System

### 5.1 LiteLLM Integration

The LiteLLM proxy runs as a Docker container and exposes an OpenAI-compatible API.
All AI calls from the backend use the standard OpenAI Python SDK pointed at
`http://litellm:4000`.

**LiteLLM config.yaml example:**

```yaml
model_list:
  - model_name: "xbot-primary"
    litellm_params:
      model: "openai/gpt-4o"
      api_key: "os.environ/OPENAI_API_KEY"
  - model_name: "xbot-fast"
    litellm_params:
      model: "openai/gpt-4o-mini"
      api_key: "os.environ/OPENAI_API_KEY"
  - model_name: "xbot-fallback"
    litellm_params:
      model: "anthropic/claude-sonnet-4-20250514"
      api_key: "os.environ/ANTHROPIC_API_KEY"

router_settings:
  routing_strategy: "simple-shuffle"
  num_retries: 2
  fallbacks:
    - xbot-primary: ["xbot-fallback"]
```

### 5.2 AI Call Types

| Call Type | Model | Purpose | Max Tokens |
|:---|:---|:---|:---|
| **Session Planning** | xbot-primary | Decide what to do this session | 2000 |
| **Content Generation** | xbot-primary | Write tweets, replies, quotes | 1000 |
| **Engagement Decision** | xbot-fast | Should I like/reply to this tweet? | 500 |
| **Feed Analysis** | xbot-fast | Summarize what's trending in the feed | 1500 |
| **Diary Entry** | xbot-fast | Write diary entry after session | 1000 |
| **Strategy Review** | xbot-primary | Weekly strategy review and adjustment | 3000 |

### 5.3 Session Planning Prompt Structure

The session planner is the brain of each cycle. It receives a large context package:

```
SYSTEM PROMPT:
  You are {persona_name}. You are operating your X (Twitter) account.
  [Full character sheet injected here — personality, interests, writing style,
   rules, goals, content pillars]

USER PROMPT:
  ## Your Current State
  - Current time: {timestamp}
  - Account age: {days} days
  - Followers: {count} | Following: {count}
  - Today's actions so far: {summary}
  - Rate budget remaining: {budget_breakdown}

  ## Your Recent Diary
  {last_3_diary_entries}

  ## Your Active Memories
  {relevant_memories — retrieved by recency + importance}

  ## Your Relationships
  {top_relationships — people you interact with frequently}

  ## Your Strategy
  {current_strategy_document}

  ## Your Performance (Last 7 Days)
  {analytics_summary}

  ## Current Feed Snapshot
  {top_20_tweets_from_feed — text + author + engagement counts}

  ## Instructions
  Based on who you are and what you see, plan your next session.
  Return a JSON array of actions you want to take, in priority order.
  Each action must include: type, target, content (if applicable), reasoning.
  Stay within your rate budget. Be strategic about what you engage with.
  Act naturally — you are a real person, not a bot.
```

### 5.4 Response Schema (Structured Output)

The AI must return valid JSON matching this schema. Use OpenAI structured output
or parse and validate with Pydantic.

```json
{
  "session_plan": {
    "mood": "string — current mood/energy level",
    "reasoning": "string — why these actions were chosen",
    "actions": [
      {
        "type": "post | reply | like | retweet | quote | follow | browse | search",
        "target": "tweet_url or username or null",
        "content": "text content for post/reply/quote, null for likes",
        "reasoning": "why this specific action",
        "priority": 1
      }
    ],
    "skip_reason": "string or null — if deciding to skip this session entirely"
  }
}
```

### 5.5 Content Generation Pipeline

For posts, replies, and quotes, the AI generates content in-character:

```
1. SESSION PLANNER decides "I should post about {topic}" or "I should reply to {tweet}"
2. CONTENT GENERATOR receives:
   - Full persona context (personality, writing style, rules)
   - The topic or tweet being replied to
   - Last 20 posts by this persona (to avoid repetition)
   - Writing style examples from persona definition
   - Content performance data (what topics/formats worked before)
3. CONTENT GENERATOR returns:
   - Primary text
   - 2 alternative versions (for future A/B testing)
   - Suggested hashtags (with confidence — persona may avoid them)
4. CONTENT VALIDATOR checks:
   - Character count (≤ 280 or ≤ 25,000 for long-form Premium)
   - No banned words/phrases from persona rules
   - Not too similar to recent posts (cosine similarity check)
   - Aligns with persona voice (basic consistency heuristic)
5. If validation fails → regenerate with feedback, max 2 retries
```

### 5.6 Engagement Decision Flow

For each tweet encountered while browsing the feed:

```
Tweet appears in feed
        │
        ▼
  Is it from a known relationship?  ──YES──► Higher engagement bias
        │ NO
        ▼
  Is it in our interest areas?  ──NO──► Skip (80%) or Like (20%)
        │ YES
        ▼
  AI QUICK EVAL: "Should {persona} engage with this?"
  (Fast model, ~500 tokens, low latency)
        │
        ▼
  Returns: { action: "like" | "reply" | "quote" | "skip",
             confidence: 0.0-1.0,
             content: "..." if reply/quote }
        │
        ▼
  Rate budget check ──► If over budget, downgrade (reply→like, like→skip)
        │
        ▼
  Execute action with human-like timing
```

---

## 6. Profile Persona & Diary System

### 6.1 File Structure Per Profile

Each profile lives at `/data/profiles/{profile_id}/`:

```
profiles/
└── techie_sarah/
    ├── persona.yaml              # Character definition (the "soul" — rarely changes)
    ├── config.yaml               # Operational config (schedule, limits, proxy, creds)
    ├── strategy.yaml             # Current strategy (AI-updated weekly)
    ├── diary/
    │   ├── 2026-06-18.md         # Daily diary entries (appended throughout the day)
    │   ├── 2026-06-17.md
    │   └── ...
    ├── memories/
    │   ├── episodic.jsonl        # Timestamped event memories
    │   ├── semantic.jsonl        # Learned facts and opinions
    │   └── important.jsonl       # Starred/high-importance memories
    ├── relationships/
    │   └── known_accounts.yaml   # People this persona knows about
    ├── content/
    │   ├── drafts.jsonl          # Unpublished content ideas
    │   └── templates.yaml        # Recurring content formats
    └── browser_data/             # Playwright persistent context
        └── Default/
            ├── Cookies
            ├── Local Storage/
            └── ...
```

### 6.2 Persona Definition Schema (`persona.yaml`)

```yaml
# persona.yaml — The soul of the character. Rarely modified once set.
id: "techie_sarah"
display_name: "Sarah Chen"
x_handle: "@sarahcodes"

# === IDENTITY ===
identity:
  age: 29
  location: "San Francisco, CA"
  occupation: "Senior Software Engineer at a mid-stage startup"
  education: "BS Computer Science, UC Berkeley"
  background: |
    Sarah grew up in the Bay Area. She's been coding since 14,
    starting with Python and falling in love with systems programming.
    She leads the backend team at her current startup.

# === PERSONALITY ===
personality:
  traits:
    - "Curious and always learning"
    - "Dry sense of humor"
    - "Opinionated but open to being wrong"
    - "Supportive of junior developers"
  values:
    - "Open source software"
    - "Mentorship"
    - "Work-life balance"
    - "Technical excellence without gatekeeping"
  communication_style: |
    Casual, conversational tone. Uses lowercase often but not always.
    Occasional emoji (🤔, 💀, 🚀) but never excessive. Threads long
    thoughts. Doesn't use hashtags much.

# === KNOWLEDGE & INTERESTS ===
interests:
  primary:
    - "Rust programming"
    - "Distributed systems"
    - "Developer tools"
    - "Open source"
  secondary:
    - "Coffee"
    - "Hiking in Marin"
    - "Mechanical keyboards"
  will_not_discuss:
    - "Partisan politics"
    - "Crypto/web3"

# === WRITING STYLE ===
writing_style:
  tone: "casual-professional"
  typical_length: "short-to-medium (1-3 sentences)"
  formatting:
    - "Rarely uses hashtags"
    - "Threads for long-form thoughts"
    - "Uses code snippets when relevant"
  examples:
    - "hot take: the best documentation is the code you didn't have to write"
    - "just spent 3 hours debugging a race condition that turned out to be a typo. AMA."
    - "genuinely impressed by the new cargo workspace features. rust keeps shipping 🚀"

# === GOALS ===
goals:
  short_term:
    - "Grow to 1,000 followers in 3 months"
    - "Establish reputation in Rust community"
  long_term:
    - "Become a recognized voice in developer tools"
    - "Hit monetization thresholds"
  content_pillars:
    - "Technical insights and tips (40%)"
    - "Developer culture commentary (25%)"
    - "Personal/relatable moments (20%)"
    - "Community engagement / reacting to news (15%)"

# === RULES & BOUNDARIES ===
rules:
  always:
    - "Stay in character"
    - "Be helpful and genuine"
    - "Credit others' work"
    - "Engage meaningfully, not superficially"
  never:
    - "Post about topics in will_not_discuss"
    - "Be mean or dismissive"
    - "Shill products or services"
    - "Copy someone else's tweet"
    - "Use engagement bait phrases"
```

### 6.3 Diary System

The diary is the persona's "inner monologue" — written by the AI after each
session. One markdown file per day, appended throughout the day.

**Example diary entry:**

```markdown
# Diary — 2026-06-18

## Session 1 (09:15 AM)
**Mood:** Energetic, had coffee
**What I did:**
- Posted about the new Rust 1.82 release — felt good about the take
- Liked 4 tweets from @rustlang and @withoutboats
- Replied to @devjokes with a sarcastic one-liner

**What I learned:**
- The Rust community is buzzing about async trait improvements
- @bob_systems is working on something similar to my side project

**How it went:**
- The Rust post got 12 likes in the first hour — above my average

**Thoughts for next time:**
- Should post more about async Rust — engagement is strong
- Consider reaching out to @alice_dev with a thoughtful reply
```

### 6.4 Memory System

Memories are stored as JSONL (one JSON object per line) for efficient append-only
writes and streaming reads.

**Episodic Memories** — Events that happened:
```json
{"ts": "2026-06-18T09:15:00Z", "type": "episodic", "event": "posted_tweet", "content": "Posted about Rust 1.82 release", "tweet_id": "...", "outcome": "12 likes in first hour", "importance": 0.6}
```

**Semantic Memories** — Things learned:
```json
{"ts": "2026-06-18T09:20:00Z", "type": "semantic", "fact": "@alice_dev is a systems programmer interested in Rust", "source": "her profile bio", "confidence": 0.8, "importance": 0.5}
```

**Important Memories** — Starred for persistent recall:
```json
{"ts": "2026-06-18T09:25:00Z", "type": "important", "content": "Threading about async Rust gets 3x normal engagement", "evidence": "last 3 async posts averaged 40 likes vs 13 overall", "importance": 1.0}
```

### 6.5 Memory Retrieval Strategy

When assembling context for an AI call, memories are retrieved by:

1. **Recency** — Last 50 episodic memories (covers ~2-3 days)
2. **Importance** — All memories with `importance >= 0.8`
3. **Relevance** — If replying to a specific user, pull all memories mentioning them
4. **Token Budget** — Total memory context capped at ~4,000 tokens; trimmed by
   lowest importance score when budget is exceeded

### 6.6 Relationship Tracking (`known_accounts.yaml`)

```yaml
accounts:
  alice_dev:
    display_name: "Alice Developer"
    first_seen: "2026-06-15"
    relationship: "mutual interest in Rust"
    sentiment: "positive"
    interaction_count: 7
    last_interaction: "2026-06-18"
    notes: "She followed me first. Posts great systems content."

  bob_systems:
    display_name: "Bob Systems"
    first_seen: "2026-06-10"
    relationship: "working on similar projects"
    sentiment: "neutral-positive"
    interaction_count: 3
    last_interaction: "2026-06-16"
    notes: "His async runtime project looks interesting."
```

Relationships are updated after each session by the AI. The AI decides:
- Whether to create a new relationship entry for someone interacted with
- Whether to update sentiment or notes for existing relationships
- Which accounts to prioritize for future engagement

### 6.7 Strategy Document (`strategy.yaml`)

```yaml
last_updated: "2026-06-15"
review_period: "weekly"

current_focus:
  primary: "Establish presence in Rust community"
  secondary: "Build relationships with 10 key accounts"

content_strategy:
  posting_frequency: "3-5 tweets per day"
  best_times: ["09:00-10:00", "12:00-13:00", "17:00-18:00"]
  top_performing_topics: ["async rust", "developer tools"]
  underperforming_topics: ["mechanical keyboards"]

engagement_strategy:
  daily_targets:
    likes: 15-25
    replies: 5-10
    follows: 2-5
  priority_accounts: ["@rustlang", "@withoutboats", "@alice_dev"]

growth_observations:
  - "Threading gets 3x more impressions than single tweets"
  - "Posting before 10 AM PST has higher engagement"

adjustments:
  - "Increase threading frequency from 2x/week to 3x/week"
  - "Reduce keyboard content, increase dev tools content"
```

This document is updated weekly by an AI strategy review that analyzes the past
week's analytics and adjusts the approach.

---

## 7. Database Design

### 7.1 Entity-Relationship Overview

```
PROFILES ──1:N──► SESSIONS ──1:N──► ACTIONS ──1:1──► ACTION_RESULTS
    │                                   │
    ├──1:N──► ANALYTICS_SNAPSHOTS       │
    ├──1:N──► CONTENT ◄─────────────────┘
    └──1:N──► RATE_LIMITS
```

### 7.2 Table Definitions

**profiles**

| Column | Type | Notes |
|:---|:---|:---|
| id | UUID (PK) | |
| profile_slug | VARCHAR UNIQUE | e.g. "techie_sarah" — maps to filesystem directory |
| x_handle | VARCHAR | e.g. "@sarahcodes" |
| display_name | VARCHAR | e.g. "Sarah Chen" |
| status | ENUM | `active`, `paused`, `locked`, `suspended` |
| persona_summary | JSONB | Cached summary from persona.yaml for quick API access |
| config | JSONB | Operational config (schedule, rate limits, proxy) |
| proxy_url_encrypted | TEXT | Fernet-encrypted proxy URL |
| created_at | TIMESTAMP | |
| last_session_at | TIMESTAMP | |

**sessions**

| Column | Type | Notes |
|:---|:---|:---|
| id | UUID (PK) | |
| profile_id | UUID (FK → profiles) | |
| started_at | TIMESTAMP | |
| ended_at | TIMESTAMP | |
| status | ENUM | `running`, `completed`, `failed`, `aborted` |
| plan | JSONB | AI-generated session plan |
| summary | JSONB | Post-session AI summary |
| actions_planned | INT | |
| actions_completed | INT | |
| actions_failed | INT | |
| error_log | TEXT | |

**actions**

| Column | Type | Notes |
|:---|:---|:---|
| id | UUID (PK) | |
| session_id | UUID (FK → sessions) | |
| profile_id | UUID (FK → profiles) | For direct profile queries |
| action_type | ENUM | `post`, `reply`, `like`, `retweet`, `quote`, `follow`, `browse`, `search` |
| target_url | VARCHAR | Tweet URL or profile URL |
| content | TEXT | Post/reply text content |
| status | ENUM | `pending`, `executing`, `completed`, `failed`, `skipped` |
| result | JSONB | Action-specific result data |
| duration_ms | INT | How long the action took |
| executed_at | TIMESTAMP | |
| error | TEXT | Error message if failed |

**action_results** (engagement tracking for posted content)

| Column | Type | Notes |
|:---|:---|:---|
| id | UUID (PK) | |
| action_id | UUID (FK → actions) | |
| tweet_id | VARCHAR | X's tweet ID |
| initial_likes | INT | Captured right after posting |
| initial_retweets | INT | |
| initial_replies | INT | |
| initial_views | INT | |
| raw_data | JSONB | Any additional scraped data |
| captured_at | TIMESTAMP | |

**analytics_snapshots** (daily profile health)

| Column | Type | Notes |
|:---|:---|:---|
| id | UUID (PK) | |
| profile_id | UUID (FK → profiles) | |
| snapshot_date | DATE | One per day per profile |
| followers | INT | |
| following | INT | |
| total_tweets | INT | |
| impressions_24h | INT | If available |
| engagements_24h | INT | |
| engagement_rate | FLOAT | |
| top_tweets | JSONB | Best performing content IDs |
| captured_at | TIMESTAMP | |

**content** (all generated content with performance tracking)

| Column | Type | Notes |
|:---|:---|:---|
| id | UUID (PK) | |
| profile_id | UUID (FK → profiles) | |
| content_type | ENUM | `original`, `reply`, `quote`, `thread` |
| body | TEXT | The actual content |
| status | ENUM | `draft`, `posted`, `failed` |
| tweet_id | VARCHAR | X's ID after posting |
| performance | JSONB | Engagement over time (likes, RTs, views) |
| ai_metadata | JSONB | Topic, intent, alternatives generated |
| posted_at | TIMESTAMP | |
| created_at | TIMESTAMP | |

**rate_limits** (current rate state per profile)

| Column | Type | Notes |
|:---|:---|:---|
| id | UUID (PK) | |
| profile_id | UUID (FK → profiles) | |
| action_type | VARCHAR | |
| count_today | INT | |
| count_this_hour | INT | |
| window_start | TIMESTAMP | |
| last_action_at | TIMESTAMP | |
| cooldown_until | TIMESTAMP | NULL if no cooldown active |

### 7.3 Key Indexes

```sql
CREATE INDEX idx_sessions_profile_started ON sessions(profile_id, started_at DESC);
CREATE INDEX idx_actions_profile_type     ON actions(profile_id, action_type, executed_at DESC);
CREATE INDEX idx_actions_session          ON actions(session_id);
CREATE INDEX idx_analytics_profile_date   ON analytics_snapshots(profile_id, snapshot_date DESC);
CREATE INDEX idx_rate_limits_profile_type ON rate_limits(profile_id, action_type);
CREATE INDEX idx_content_profile_posted   ON content(profile_id, posted_at DESC);
CREATE INDEX idx_content_performance      ON content USING gin(performance);
```

### 7.4 Migration Strategy

- Use **Alembic** for schema migrations, integrated with SQLAlchemy models
- Migration files version-controlled in `backend/migrations/versions/`
- Auto-generate migrations: `alembic revision --autogenerate -m "description"`
- Always test migrations in dev before applying to production
- Every migration has a corresponding downgrade path

---

## 8. Scheduling & Orchestration

### 8.1 Schedule Architecture

```
┌────────────────────────────────────────────────────┐
│                  CELERY BEAT                        │
│  Runs every 60 seconds, checks:                    │
│  - Which profiles are due for a session?           │
│  - Any pending manual triggers?                    │
│  - Any analytics snapshots due?                    │
│  - Any strategy reviews due?                       │
└───────────────────────┬────────────────────────────┘
                        │
                        ▼
┌────────────────────────────────────────────────────┐
│              PROFILE SCHEDULER                      │
│  For each due profile:                             │
│  1. Check if profile is active (not paused/locked) │
│  2. Check rate budget (not exhausted for the day)  │
│  3. Check no session already running (Redis lock)  │
│  4. Check cooldown (min 30 min between sessions)   │
│  5. Submit run_session task to Celery worker queue  │
└───────────────────────┬────────────────────────────┘
                        │
                        ▼
┌────────────────────────────────────────────────────┐
│              CELERY WORKER                          │
│  Execute session task:                             │
│  1. Assemble context                               │
│  2. Call AI for session plan                       │
│  3. Launch browser                                 │
│  4. Execute actions                                │
│  5. Post-process (diary, memories, analytics)      │
│  6. Release resources                              │
└────────────────────────────────────────────────────┘
```

### 8.2 Profile Schedule Configuration

Each profile has its schedule defined in `config.yaml`:

```yaml
schedule:
  type: "natural"  # "natural" | "fixed" | "manual"

  # For "natural" scheduling — mimics human activity patterns
  natural:
    timezone: "America/Los_Angeles"
    wake_hour: 8           # Don't start before 8 AM local
    sleep_hour: 23         # Don't run after 11 PM local
    sessions_per_day: 4    # Target number of sessions
    min_gap_minutes: 60    # Minimum time between sessions

    # Day-of-week activity weights (0=Mon, 6=Sun)
    day_weights:
      0: 1.0    # Monday — normal
      1: 1.0    # Tuesday
      2: 1.0    # Wednesday
      3: 1.0    # Thursday
      4: 1.2    # Friday — slightly more active
      5: 0.7    # Saturday — less active
      6: 0.5    # Sunday — least active

  # For "fixed" scheduling
  fixed:
    cron: "0 9,12,17,21 * * 1-5"  # Weekdays at 9, 12, 5, 9
```

### 8.3 Natural Schedule Algorithm

```
1. At startup (and daily at midnight profile-local-time), generate the day's
   session times:
   a. Pick N = round(sessions_per_day × day_weight_for_today)
   b. Divide awake hours (wake_hour → sleep_hour) into N equal windows
   c. For each window, pick a random time within it
   d. Add jitter: ±15 minutes
   e. Store schedule in Redis as sorted set: schedule:{profile_id}:{date}

2. Every 60s, Celery Beat checks:
   - For each active profile, is any scheduled time in the past but not yet
     executed?
   - If yes → submit session task to worker queue

3. After each session completes, record actual completion time in DB.
   Next session must respect min_gap_minutes from this time.

4. Occasionally (10% chance), skip a scheduled session entirely — simulates
   the human being busy or distracted. Log skip reason as "natural_skip".
```

### 8.4 Task Types

| Task | Trigger | Priority | Timeout |
|:---|:---|:---|:---|
| `session.run` | Schedule or manual | NORMAL | 30 min |
| `analytics.snapshot` | Daily at 3 AM (profile TZ) | LOW | 10 min |
| `strategy.review` | Weekly on Sunday | LOW | 5 min |
| `content.generate_drafts` | Daily | LOW | 5 min |
| `maintenance.cleanup_old_logs` | Daily at 4 AM | LOW | 15 min |
| `maintenance.backup_profiles` | Daily at 5 AM | LOW | 30 min |

---

## 9. Rate Limits & Safety

### 9.1 Three-Tier Rate Limit Architecture

```
┌─────────────────────────────────────────┐
│  LEVEL 1: HARD LIMITS (absolute caps)   │
│  Redis counters — cannot be exceeded    │
└────────────────────┬────────────────────┘
                     │
┌────────────────────▼────────────────────┐
│  LEVEL 2: SOFT LIMITS (daily budgets)   │
│  Per-profile config — AI plans within   │
└────────────────────┬────────────────────┘
                     │
┌────────────────────▼────────────────────┐
│  LEVEL 3: BEHAVIORAL LIMITS             │
│  Session-level pacing + human timing    │
└─────────────────────────────────────────┘
```

### 9.2 Hard Limits (Defaults — Established Accounts)

| Action | Per Hour | Per Day | Cooldown Between Actions |
|:---|:---|:---|:---|
| Posts (original) | 3 | 15 | 20-45 min |
| Replies | 5 | 30 | 5-15 min |
| Likes | 10 | 50 | 30-90 sec |
| Retweets | 3 | 15 | 10-30 min |
| Quote tweets | 2 | 10 | 20-45 min |
| Follows | 3 | 15 | 10-30 min |
| Unfollows | 2 | 10 | 10-30 min |
| DMs | 2 | 10 | 30-60 min |

> **New accounts (< 30 days)** operate at **50%** of these values.
> **Growing accounts (30-90 days)** operate at **75%**.
> These are configurable per profile.

### 9.3 Soft Limits (Per-Profile Budget)

```yaml
# In profile config.yaml
rate_limits:
  account_age_days: 90
  tier: "established"  # "new" | "growing" | "established"

  daily_budget:
    posts: 5
    replies: 15
    likes: 30
    retweets: 5
    quote_tweets: 3
    follows: 5

  session_budget:
    max_actions: 20          # Max actions per session
    max_duration_minutes: 25 # Max session length
```

### 9.4 Redis Implementation

```
Key pattern:    rate:{profile_id}:{action_type}:{window}
Examples:       rate:techie_sarah:like:hourly
                rate:techie_sarah:post:daily

Implementation: Redis sorted sets with timestamps as scores
  ZADD   → record each action timestamp
  ZCOUNT → count actions in time window
  ZREMRANGEBYSCORE → prune expired entries

Cooldown tracking:
  Key:    cooldown:{profile_id}:{action_type}
  Value:  timestamp when cooldown expires
  TTL:    auto-expire after max cooldown duration
```

### 9.5 Account Safety Measures

| Measure | Implementation |
|:---|:---|
| **Warm-up period** | New profiles: 25% limits week 1, 50% week 2, 75% week 3, 100% week 4 |
| **Session variance** | No two consecutive sessions have identical action patterns |
| **Daily variance** | Total daily actions vary ±30% day-to-day randomly |
| **Weekend patterns** | Reduced activity on weekends (configurable day_weights) |
| **Engagement ratio** | Maintain likes:posts ratio ≥ 3:1 (natural human behavior) |
| **Follow ratio** | Track follow/unfollow ratio; never > 10% churn per week |
| **Content uniqueness** | Cosine similarity against last 100 posts; reject if > 70% similar |
| **Activity gaps** | Skip 10% of scheduled sessions randomly (simulate being busy) |
| **Progressive backoff** | Any 429 or suspicious response → reduce all limits 50% for 24h |
| **Circuit breaker** | 3 consecutive failures → pause 6h; 3 pauses in a week → manual review |

### 9.6 Health Signal Detection

The system continuously monitors for warning signs:

| Signal | Detection | Response |
|:---|:---|:---|
| Follower count drops suddenly | Analytics snapshot delta > -5% | Reduce activity, flag for review |
| Impressions collapse | 7-day rolling average drops > 50% | Possible shadowban — pause 48h |
| Login challenges appear | Browser detects CAPTCHA/verify page | Pause, screenshot, notify admin |
| "Unusual activity" warning | Browser detects X warning banner | Immediate pause, notify admin |
| Account locked | Login fails after session restore | Mark profile LOCKED, stop all activity |
| Engagement rate tanks | Content scores trend downward | AI strategy review triggered early |

---

## 10. Analytics & Strategy Engine

### 10.1 Data Collection

| Metric | Source | Frequency |
|:---|:---|:---|
| Follower count | Profile page scrape | Every session |
| Following count | Profile page scrape | Every session |
| Tweet engagement (likes, replies, RTs) | Tweet detail page scrape | Every session |
| Tweet views/impressions | Tweet analytics (if visible) | Every session |
| Profile visits | X analytics page (if Premium) | Daily snapshot |
| Top-performing tweets | Sort by engagement score | Daily |

### 10.2 Analytics Snapshot Process

Daily at 3 AM (profile timezone):

1. Open browser session for the profile
2. Navigate to the profile page
3. Capture follower count, following count
4. Scrape recent tweet performance (last 20 tweets)
5. Navigate to analytics page if accessible
6. Store snapshot in `analytics_snapshots` table
7. Compare with previous snapshot → compute deltas
8. Store deltas for trend analysis

### 10.3 Performance Scoring

Each piece of content receives a composite score:

```
EngagementScore = (likes × 1) + (replies × 3) + (retweets × 5) + (quotes × 7)
ReachScore      = views (if available, else estimate from engagement)
EfficiencyScore = EngagementScore / ReachScore  (engagement rate)
```

Content is tagged with topics (extracted by AI at creation time) and scored to
identify:

- **Top-performing topics** — what the audience responds to
- **Best posting times** — time-of-day engagement correlation
- **Best content formats** — threads vs. single tweets vs. with-media
- **Best engagement targets** — which accounts to interact with for visibility

### 10.4 Strategy Engine (Weekly Review)

Every week, the AI reviews analytics and updates `strategy.yaml`:

```
INPUT to AI:
  - Last 7 days of analytics snapshots
  - Performance scores for all content posted this week
  - Follower growth trend (week-over-week)
  - Top 5 and bottom 5 performing posts (with topics)
  - Current strategy document
  - Persona goals and content pillars

OUTPUT from AI:
  - Updated strategy.yaml with:
    - Adjusted content pillar percentages
    - Updated best posting times
    - Updated priority accounts for engagement
    - New growth observations
    - Specific adjustments for next week
    - Monetization progress notes
```

### 10.5 Monetization Tracking

The system tracks progress toward X's monetization thresholds:

```yaml
# Computed and stored in analytics
monetization_status:
  x_premium_active: true
  stripe_connected: false

  ads_revenue_sharing:
    eligible: false
    progress:
      followers: { current: 347, required: 500, pct: 69 }
      impressions_3mo: { current: 1200000, required: 5000000, pct: 24 }
    estimated_eligibility_date: "2026-09-15"  # Based on current growth rate

  creator_subscriptions:
    eligible: false
    progress:
      followers: { current: 347, required: 2000, pct: 17 }
      impressions_3mo: { current: 1200000, required: 5000000, pct: 24 }
```

Eligibility dates are projected using a simple linear regression on the
follower/impression growth rate over the last 30 days.

---

## 11. Admin Dashboard

### 11.1 Dashboard Pages

| Page | Purpose |
|:---|:---|
| **Overview** | All profiles at a glance — status, followers, today's activity, health |
| **Profile Detail** | Deep dive into one profile — persona, diary, memories, analytics |
| **Session Log** | Timeline of all sessions — plan, actions, outcomes, errors |
| **Content Library** | All posts/replies with performance data, filtering, search |
| **Analytics** | Charts: follower growth, engagement trends, content performance |
| **Monetization** | Progress bars toward monetization thresholds per profile |
| **Rate Limits** | Current rate limit state, budget remaining, cooldown timers |
| **Settings** | System config, LiteLLM settings, proxy config, notifications |
| **Persona Editor** | Edit persona YAML with preview; validate character consistency |

### 11.2 Key Features

- **Real-time session monitoring** via WebSocket — watch actions as they execute
- **Manual trigger** — start a session for any profile immediately
- **Pause/resume** — pause a single profile or the entire system
- **Content approval mode** — optional: AI generates, human approves before posting
- **Diary viewer** — read any profile's diary in a timeline format
- **Health alerts** — banner notifications for critical events
- **Dark mode** — default, with light mode toggle

### 11.3 API Endpoints (FastAPI)

```
# === Profiles ===
GET    /api/profiles                     — List all profiles
POST   /api/profiles                     — Create new profile
GET    /api/profiles/{id}                — Get profile detail
PUT    /api/profiles/{id}                — Update profile
DELETE /api/profiles/{id}                — Delete profile
POST   /api/profiles/{id}/pause          — Pause profile
POST   /api/profiles/{id}/resume         — Resume profile
POST   /api/profiles/{id}/trigger        — Manual session trigger

# === Sessions ===
GET    /api/profiles/{id}/sessions       — List sessions for profile
GET    /api/sessions/{id}                — Session detail
GET    /api/sessions/{id}/actions        — Actions within session
WS     /api/sessions/{id}/live           — Live session WebSocket feed

# === Content ===
GET    /api/profiles/{id}/content        — List content for profile
GET    /api/content/{id}                 — Content detail with performance

# === Analytics ===
GET    /api/profiles/{id}/analytics      — Analytics data (date range param)
GET    /api/profiles/{id}/monetization   — Monetization progress

# === Persona Data ===
GET    /api/profiles/{id}/persona        — Get persona YAML
PUT    /api/profiles/{id}/persona        — Update persona YAML
GET    /api/profiles/{id}/diary          — Get diary entries (date range)
GET    /api/profiles/{id}/memories       — Get memories (paginated)
GET    /api/profiles/{id}/relationships  — Get relationship data
GET    /api/profiles/{id}/strategy       — Get current strategy

# === System ===
GET    /api/health                       — System health check
GET    /api/rate-limits                  — All rate limit states
POST   /api/system/pause                 — Pause entire system
POST   /api/system/resume                — Resume entire system
GET    /api/system/config                — Get system configuration
PUT    /api/system/config                — Update system configuration
```

---

## 12. Docker & Portainer Deployment

### 12.1 Docker Compose

```yaml
version: "3.9"

services:
  # === DATABASE ===
  postgres:
    image: postgres:16-alpine
    restart: unless-stopped
    environment:
      POSTGRES_USER: ${DB_USER:-xbot}
      POSTGRES_PASSWORD: ${DB_PASSWORD}
      POSTGRES_DB: ${DB_NAME:-xbot}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DB_USER:-xbot}"]
      interval: 10s
      timeout: 5s
      retries: 5

  # === CACHE & BROKER ===
  redis:
    image: redis:7-alpine
    restart: unless-stopped
    command: redis-server --requirepass ${REDIS_PASSWORD}
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "--no-auth-warning", "-a", "${REDIS_PASSWORD}", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  # === AI GATEWAY ===
  litellm:
    image: ghcr.io/berriai/litellm:main-stable
    restart: unless-stopped
    ports:
      - "${LITELLM_PORT:-4000}:4000"
    environment:
      - LITELLM_MASTER_KEY=${LITELLM_MASTER_KEY}
      - DATABASE_URL=postgresql://${DB_USER:-xbot}:${DB_PASSWORD}@postgres:5432/litellm
    volumes:
      - ./config/litellm_config.yaml:/app/config.yaml:ro
    depends_on:
      postgres:
        condition: service_healthy

  # === API SERVER ===
  api:
    build:
      context: .
      dockerfile: docker/Dockerfile.api
    restart: unless-stopped
    ports:
      - "${API_PORT:-8000}:8000"
    environment:
      - DATABASE_URL=postgresql+asyncpg://${DB_USER:-xbot}:${DB_PASSWORD}@postgres:5432/${DB_NAME:-xbot}
      - REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379/0
      - LITELLM_BASE_URL=http://litellm:4000
      - LITELLM_API_KEY=${LITELLM_MASTER_KEY}
      - SECRET_KEY=${SECRET_KEY}
    volumes:
      - profile_data:/data/profiles
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy

  # === CELERY WORKER (Browser Automation) ===
  worker:
    build:
      context: .
      dockerfile: docker/Dockerfile.worker
    restart: unless-stopped
    init: true          # Reap zombie browser processes
    ipc: host           # Chromium shared memory requirement
    environment:
      - DATABASE_URL=postgresql+asyncpg://${DB_USER:-xbot}:${DB_PASSWORD}@postgres:5432/${DB_NAME:-xbot}
      - REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379/0
      - LITELLM_BASE_URL=http://litellm:4000
      - LITELLM_API_KEY=${LITELLM_MASTER_KEY}
      - SECRET_KEY=${SECRET_KEY}
    volumes:
      - profile_data:/data/profiles
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy

  # === CELERY BEAT (SCHEDULER) ===
  scheduler:
    build:
      context: .
      dockerfile: docker/Dockerfile.worker
    restart: unless-stopped
    command: celery -A xbot.celery_app beat --loglevel=info
    environment:
      - DATABASE_URL=postgresql+asyncpg://${DB_USER:-xbot}:${DB_PASSWORD}@postgres:5432/${DB_NAME:-xbot}
      - REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379/0
    depends_on:
      redis:
        condition: service_healthy

  # === DASHBOARD ===
  dashboard:
    build:
      context: .
      dockerfile: docker/Dockerfile.dashboard
    restart: unless-stopped
    ports:
      - "${DASHBOARD_PORT:-3000}:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://api:8000
    depends_on:
      - api

volumes:
  postgres_data:
  redis_data:
  profile_data:
```

### 12.2 Dockerfile Strategy

| Image | Base | Key Notes |
|:---|:---|:---|
| `Dockerfile.api` | `python:3.12-slim` | Install deps via uv, copy backend/, run uvicorn |
| `Dockerfile.worker` | `mcr.microsoft.com/playwright/python:v1.52.0-noble` | Pre-installed Chromium, install Python deps, run celery worker |
| `Dockerfile.dashboard` | `node:22-alpine` | Install deps, build Next.js, run with `next start` |

The worker image is based on Microsoft's official Playwright Docker image which
includes all system dependencies for Chromium. This avoids dependency hell.

### 12.3 Portainer Setup

1. **Install Portainer CE** on the Docker host:
   ```bash
   docker volume create portainer_data
   docker run -d -p 9443:9443 --name portainer \
     --restart=always \
     -v /var/run/docker.sock:/var/run/docker.sock \
     -v portainer_data:/data \
     portainer/portainer-ce:latest
   ```

2. **Deploy XBot as a Stack:**
   - Portainer UI → Stacks → Add Stack
   - Paste `docker-compose.yml` content
   - Add environment variables (DB_PASSWORD, REDIS_PASSWORD, etc.)
   - Deploy

3. **Manage through Portainer:**
   - View container logs in real-time
   - Restart individual services
   - Scale workers (increase `worker` replicas)
   - Update images (pull latest, redeploy)
   - Monitor CPU, memory, network per container

### 12.4 Volume Strategy

| Volume | Content | Backup Priority |
|:---|:---|:---|
| `postgres_data` | All database state | **CRITICAL** — daily pg_dump |
| `redis_data` | Cache, rate counters | Low — fully reconstructible |
| `profile_data` | Persona files, diary, memories, browser sessions | **CRITICAL** — daily tar backup |

---

## 13. Security & Secrets

### 13.1 Secret Management

| Secret | Storage | Notes |
|:---|:---|:---|
| DB password | `.env` file | Passed to Docker Compose |
| Redis password | `.env` file | |
| LiteLLM master key | `.env` file | Used as API key for backend to call proxy |
| LLM provider API keys | LiteLLM `config.yaml` | Referenced via `os.environ/KEY_NAME` |
| Dashboard auth token | `.env` file | Simple bearer token for single-tenant UI |
| Encryption secret | `.env` file | `SECRET_KEY` used for Fernet |
| X credentials | Profile `config.yaml` | Encrypted at rest (see 13.2) |
| Proxy credentials | Profile `config.yaml` | Encrypted at rest |

**Important:** The `.env` file must never be committed to version control.

### 13.2 Credential Encryption

To protect sensitive X logins and proxies in case the file system is compromised:

```yaml
# config.yaml (on disk)
credentials:
  x_username: "ENC:gAAAAABh..."   # Fernet-encrypted with SECRET_KEY
  x_password: "ENC:gAAAAABh..."
  proxy_url: "ENC:gAAAAABh..."
```

1. The dashboard uses the `SECRET_KEY` to encrypt credentials when saving a profile.
2. The Celery worker decrypts them **only in-memory** during session launch.
3. Decrypted credentials are never logged and never sent to the LLM.

### 13.3 Network Security

- Services communicate exclusively over the internal Docker network.
- The `postgres` and `redis` ports are NOT mapped to the host.
- Only the Dashboard (`:3000`), API (`:8000`), and optionally LiteLLM (`:4000`) are mapped.
- For production self-hosting, use a reverse proxy (like Caddy or Nginx) to terminate TLS/SSL.

---

## 14. Logging & Observability

### 14.1 Logging Architecture

```
┌──────────────────┐
│  All Services    │──► stdout/stderr ──► Docker logs ──► Portainer UI
│  (structured     │
│   JSON logging)  │──► File rotation ──► /logs/{service}/{date}.jsonl
└──────────────────┘
```

### 14.2 Log Categories & Levels

| Category | Level | Examples |
|:---|:---|:---|
| `session` | INFO | "Session started for @sarahcodes", "Session completed" |
| `browser` | DEBUG | "Navigating to feed", "Waiting 3.2s", "Clicking like" |
| `ai` | INFO | "Session plan generated", "Content validation passed" |
| `rate_limit` | WARNING | "Hourly limit reached (10/10)", "Cooldown active" |
| `safety` | CRITICAL | "Account locked detected", "CAPTCHA appeared" |
| `error` | ERROR | "Element not found: tweet-reply-button" |

### 14.3 Monitoring & Alerting

- **Primary Monitoring:** Use Portainer UI to monitor container health, CPU, and RAM.
- **System Health:** Dashboard polls `/api/health` to show component status.
- **Critical Alerts:** If an account is locked or the circuit breaker trips, the system logs a `CRITICAL` event. (Phase 5 adds optional webhook alerts to Discord/Telegram).

---

## 15. Testing Strategy

### 15.1 The Testing Pyramid

```
        ┌───────────┐
        │ E2E Tests │  ← Fewest: Full docker stack + mock X server
        ├───────────┤
        │Integration│  ← Middle: DB ops, Redis rate limits, AI calls
        ├───────────┤
        │ Unit Tests│  ← Most: Pydantic schemas, timing logic, prompt builders
        └───────────┘
```

### 15.2 Test Categories & Tools

| Category | Scope | Tools |
|:---|:---|:---|
| **Unit** | Isolated functions, schema validation, timing engine | `pytest` |
| **Integration** | DB repositories, API endpoints, Celery tasks | `pytest-asyncio`, `httpx`, `testcontainers` |
| **Browser** | Action library against controlled DOM | `pytest-playwright` + mock server |
| **AI Output** | Parsing complex LLM responses, token management | `pytest` (using cached/recorded AI responses via VCR.py) |

### 15.3 Mock X Server

To test browser automation without risking real accounts or dealing with X's rate limits:
- Build a simple local web server (e.g., using FastAPI or Express).
- Serve static HTML pages that mimic the DOM structure of X's feed, profiles, and compose box.
- Point the browser manager to `http://localhost:9999` during testing instead of `x.com`.

---

## 16. Development Phases & Backlog

### 16.1 Phase 0: Foundation (Week 1-2)
**Goal:** Project skeleton, infrastructure, basic API
- [x] Initialize Python project (uv, ruff, mypy, FastAPI)
- [x] Set up Docker Compose (Postgres, Redis, LiteLLM) — *Postgres replaced by SQLite natively as per sandbox boundaries*
- [x] Create SQLAlchemy models and Alembic migrations
- [x] Build basic FastAPI profile CRUD endpoints
- [x] Set up Celery worker and beat infrastructure
- [x] Configure Portainer stack — *Skipped due to developer sandbox constraint*

### 16.2 Phase 1: Browser Engine + Persona (Week 3-5)
**Goal:** Browser automation works, personas are loaded
- [x] Build BrowserManager with Playwright and stealth config
- [x] Build action library (browse, like, post, reply, follow)
- [x] Implement timing engine with human-like delays
- [x] Build persona YAML loader and memory/diary system (JSONL)
- [x] Implement mock X server for browser testing
- [x] Build session lifecycle management and error handling

### 16.3 Phase 2: AI Brain (Week 6-8)
**Goal:** AI drives decisions, content generated in-character
- [x] Build context assembler (persona + diary + memories)
- [x] Implement session planning prompt and JSON parsing
- [x] Build content generation pipeline with validation
- [x] Implement fast engagement decision flow
- [x] Build post-session processing (update diary/memories)
- [x] Implement weekly strategy review logic

### 16.4 Phase 3: Scheduling & Safety (Week 9-10)
**Goal:** System runs autonomously with safe scheduling
- [x] Implement natural schedule algorithm (Celery Beat)
- [x] Build Redis-based sliding window rate limiter
- [x] Implement cooldowns, warm-ups, and session variance
- [x] Build circuit breaker and progressive backoff
- [x] Add health signal detection (CAPTCHA, lock out)

### 16.5 Phase 4: Analytics & Dashboard (Week 11-14)
**Goal:** Full visibility and control through UI
- [x] Build analytics snapshot collection process
- [x] Implement content performance scoring
- [x] Build monetization progress tracker
- [x] Initialize Next.js dashboard project
- [x] Build Overview, Profile Detail, and Session Log pages
- [x] Build Analytics and Rate Limits dashboards
- [x] Implement WebSocket live session monitoring
- [x] Build Persona Editor UI

### 16.6 Phase 5: Polish & Hardening (Week 15-16)
**Goal:** Production-ready and resilient
- [x] End-to-end system load testing
- [x] Finalize backup strategy for volumes
- [x] Write system documentation and runbooks
- [x] Add webhook alerting for critical events
- [x] Log rotation and cleanup tasks
- [x] Performance optimizations (browser memory management)

---

## Appendix: Target Project Structure

```
xbot/
├── backend/
│   ├── xbot/
│   │   ├── __init__.py
│   │   ├── celery_app.py          # Celery configuration
│   │   ├── config.py              # Environment variables
│   │   ├── main.py                # FastAPI entry point
│   │   │
│   │   ├── api/                   # FastAPI routes (profiles, sessions, etc.)
│   │   ├── models/                # SQLAlchemy models
│   │   ├── schemas/               # Pydantic schemas
│   │   │
│   │   ├── browser/               # Playwright automation
│   │   │   ├── manager.py         # BrowserManager
│   │   │   ├── stealth.py         # Anti-detection config
│   │   │   ├── timing.py          # Human-like delay engine
│   │   │   └── actions/           # Action implementations (like, post, etc.)
│   │   │
│   │   ├── ai/                    # AI decision system
│   │   │   ├── client.py          # LiteLLM/OpenAI wrapper
│   │   │   ├── planner.py         # Session planning
│   │   │   ├── generator.py       # Content generation
│   │   │   └── prompts/           # Prompt templates
│   │   │
│   │   ├── persona/               # Persona & diary system
│   │   │   ├── loader.py          # YAML parser
│   │   │   ├── diary.py           # Diary manager
│   │   │   └── memory.py          # JSONL memory manager
│   │   │
│   │   ├── scheduling/            # Task scheduling (natural algorithm)
│   │   ├── safety/                # Rate limits & circuit breakers
│   │   └── analytics/             # Scraping & scoring engine
│   │
│   ├── migrations/                # Alembic
│   ├── tests/                     # Pytest suite + mock X server
│   ├── pyproject.toml
│   └── uv.lock
│
├── dashboard/                     # Next.js frontend
│   ├── src/
│   │   ├── app/                   # Next.js pages
│   │   ├── components/            # React/shadcn components
│   │   └── lib/                   # API clients
│   ├── package.json
│   └── next.config.js
│
├── config/
│   └── litellm_config.yaml        # AI gateway settings
│
├── docker/
│   ├── Dockerfile.api
│   ├── Dockerfile.worker
│   └── Dockerfile.dashboard
│
├── data/                          # Mounted as volume
│   └── profiles/                  # One directory per profile
│
├── docker-compose.yml
├── .env                           # Secrets (not in Git)
└── MASTER_PLAN.md                 # This document
```

> **End of Master Plan**
>
> The system is designed to be highly modular. An engineering team can begin implementation at Phase 0, and the system becomes minimally useful (manual triggers, single profile) by the end of Phase 2.












