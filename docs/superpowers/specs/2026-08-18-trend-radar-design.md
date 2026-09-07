# Design Specification: Real-Time Trend Radar & Breaking News Takes

**Date:** 2026-08-18  
**Status:** APPROVED  
**Author:** Antigravity Engineering  
**System:** XBot Social Agent Automation (Phase 3)  

---

## 1. Executive Summary & Objective

The **Real-Time Trend Radar & Breaking News Subsystem** allows XBot personas to detect emerging narratives, breaking industry news, and trending discussions within minutes of occurrence, formulate an authoritative or witty hot take, and post it to capture high-volume search and "For You" algorithmic traffic.

On X, accounts that publish the earliest high-quality synthesis on breaking developments experience massive impression spikes (10x–50x standard posts) and gain high-intent followers who want a curated source for their niche.

---

## 2. Architecture & Data Flow

```
┌────────────────────────────────────────────────────────┐
│               1. Celery Beat Scheduler                 │
│         `check_trend_radar` periodic task (15-30m)     │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│               2. Multi-Source Ingestion                │
│  - RSS Feeds (Tech, AI, Crypto, Developer news)        │
│  - X Trending / Explore Scraper (Playwright)           │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│               3. Redis Deduplication Cache             │
│  Key: `xbot:seen_trends:<profile_id>:<article_hash>`   │
│  - If already processed in last 7 days: SKIP           │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│               4. Persona Relevance Filter              │
│  LLM filters items against `persona.interests` and     │
│  `persona.writing_style.tone`                          │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│            5. Breaking News Take Generator             │
│  - Crafts 3-bullet breakdown + 1 hot take              │
│  - Passes through `optimize_post_hook`                 │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│            6. Browser Execution or Content Queue       │
│  - Posts immediately via `ComposePost` or saves to     │
│    `Content` queue for next scheduled window           │
└────────────────────────────────────────────────────────┘
```

---

## 3. Detailed Component Specifications

### 3.1 Feed & Trend Ingestion Layer (`xbot/ai/trend_radar.py`)
- Supported Sources:
  1. **RSS / Atom Feeds**: Standard RSS parser reading configured sources (HackerNews, TechCrunch, ArXiv AI, CoinDesk, GitHub Trending RSS).
  2. **Persona Custom Feeds**: In `persona.yaml`:
     ```yaml
     trend_sources:
       rss_feeds:
         - "https://hnrss.org/frontpage"
         - "https://rss.arxiv.org/rss/cs.AI"
       keywords: ["LLM", "agent", "OpenAI", "Anthropic", "GPU", "Rust", "Python"]
     ```
- Model:
  ```python
  class TrendItem(BaseModel):
      id: str = Field(..., description="Unique hash or URL of the news item")
      title: str
      summary: str
      source_url: str
      source_name: str
      published_at: str | None = None
  ```

### 3.2 Relevance Filter & Take Synthesizer (`xbot/ai/trend_generator.py`)
- Classifies whether a `TrendItem` matches persona interests ($0.0 - 1.0$ score).
- For items scoring $> 0.7$:
  - Synthesizes a structured take:
    - **Hook**: Scroll-stopping headline.
    - **Context**: 2-3 concise bullets explaining what happened.
    - **Persona Hot Take / Implication**: Bold prediction, contrarian observation, or witty comment.
  - Automatically runs output through `optimize_post_hook`.

### 3.3 Celery Periodic Task & Queue Routing (`xbot/tasks.py`)
- Task `check_trend_radar`:
  - Iterates active profiles.
  - Fetches and filters new trend items.
  - Generates breaking takes.
  - Either executes immediate post (if within rate limits) or adds to `Content` queue with `ContentType.TWEET` and status `APPROVED`/`DRAFT`.
  - Records processed items in Redis to prevent duplicates.

---

## 4. Verification & Testing
- **Unit Tests**:
  - `test_trend_radar.py`: RSS ingestion parsing, deduplication, persona keyword filtering.
  - `test_trend_generator.py`: Relevance scoring, structured take synthesis, hook integration.
- **Integration Tests**:
  - `test_trend_task.py`: End-to-end task execution with mock RSS/trends and content queuing.
