# Design Spec: Natural Content Diversity & Context-Aware Reply Engine

**Date:** 2026-08-27  
**Status:** Approved  
**Author:** Antigravity Engineering  

---

## 1. Executive Summary & Problem Statement

### 1.1 Problem Statement
Previous iterations of XBot suffered from several synthetic patterns:
1. **Monotonous Uniform Formatting**: Generated replies were forced into rigid 140–260 character paragraphs, ending unconditionally with a question mark (`?`) or formulaic structure.
2. **Context Blindness in Replies**: The reply generator only inspected the raw text of the root tweet in isolation, missing attached media/images and the ongoing banter/roasting in the comment section.
3. **Synthetic Quote Enclosure**: Generated tweet bodies were frequently wrapped in outer quotation marks (`"..."`).
4. **Lack of Original Media/GIF Variety**: The account posted few or no genuine standalone vertical memes (4:5), reaction GIFs from Tenor, or multi-tweet threads with real scraped viral media.

### 1.2 Goals & Solutions
1. **Full-Context Room Reading**: Scrape the root tweet text, attached image descriptions, and top 8–10 visible comments before generating replies.
2. **6 Dynamic Response Modalities (AI-Driven)**:
   - `pure_gif`: Reaction GIF search query for Tenor / X with optional 1–5 word text (`"real"`, `"💀"`, `"no notes"`).
   - `emoji_reaction`: 1–2 authentic emojis (e.g. `💀`, `😭`, `🔥`, `🤌`) when the room is purely reactive.
   - `punchy_one_liner`: Short conversational punch (20–70 chars) like *"ok i agree"*, *"they are not gonna like this one"*.
   - `witty_sarcasm`: 1–2 sentences of dry humor or relatable banter matching the comments.
   - `casual_take`: Clear point of view without lecturing.
   - `in_depth_breakdown`: 2–4 sentences of technical nuance or domain analysis when the context calls for an explanation.
3. **Total Removal of Rigid Constraints**: No forced `?` endings, no artificial length floors, and 100% outer quotation mark stripping.
4. **Autonomous Multi-Format Creation Pipeline**: Dynamically synthesize 4:5 vertical memes/infographics, rich 3–5 tweet threads attaching downloaded viral media, interactive community polls, and punchy hot takes based on topic depth.
5. **Native Browser GIF & Media Execution**: Automate the X / Tenor GIF picker and file upload handlers inside `ReplyToTweet` and `ComposePost`.

---

## 2. System Architecture & Component Design

```
+---------------------------------------------------------------------------------------------------+
| 1. CONTEXT EXTRACTION LAYER (Playwright Browser Queue)                                            |
|    - scrape_target_tweet_context(): Scrapes root text + author + images + top 10 comments & likes  |
+---------------------------------------------------------------------------------------------------+
                                                  │
                                                  ▼
+---------------------------------------------------------------------------------------------------+
| 2. AI ROOM-READER & DYNAMIC MODALITY ENGINE (xbot/ai/sniper.py)                                   |
|    - Evaluates complete context + top comments                                                    |
|    - Selects 1 of 6 response modes (pure_gif, emoji_reaction, one_liner, sarcasm, take, breakdown) |
|    - Outputs DynamicReplyResult (reply_text, gif_query, response_mode, reasoning)                 |
+---------------------------------------------------------------------------------------------------+
                                                  │
                                                  ▼
+---------------------------------------------------------------------------------------------------+
| 3. ANTI-MONOTONY FORMATTING & GATEKEEPER (xbot/ai/formatting_engine.py & anti_ai_gatekeeper.py)   |
|    - Strips outer surrounding quotes ("...", '...', “...”)                                        |
|    - Preserves short authentic reactions (<30 chars) without forced padding                       |
|    - Enforces natural double-line spacing for multi-sentence takes                                |
+---------------------------------------------------------------------------------------------------+
                                                  │
                                                  ▼
+---------------------------------------------------------------------------------------------------+
| 4. BROWSER EXECUTION LAYER (xbot/browser/actions/x_actions.py & browser_queue.py)                 |
|    - Native X / Tenor GIF picker interaction (searches gif_query and clicks top GIF)              |
|    - File upload handling for generated 4:5 memes & scraped research media                        |
|    - Multi-tweet thread composition via (+) Add Tweet button                                      |
+---------------------------------------------------------------------------------------------------+
```

---

## 3. Detailed Component Specifications

### 3.1 Context-Enriched Sniper & Reply Engine (`xbot/ai/sniper.py`)

#### Schema
```python
class DynamicReplyResult(BaseModel):
    response_mode: Literal[
        "pure_gif",
        "emoji_reaction",
        "punchy_one_liner",
        "witty_sarcasm",
        "casual_take",
        "in_depth_breakdown",
    ] = Field(..., description="The chosen response modality matching the room context")
    reply_text: str = Field(..., description="The authentic reply text (can be 1 word, 1 emoji, or a full explanation)")
    gif_query: str | None = Field(default=None, description="Search phrase for Tenor / X GIF picker when visual humor fits")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    reasoning: str = Field(default="", description="Why this response mode and angle was chosen")
```

#### System Prompt Instructions:
- **Zero Question Forcing**: Do NOT force a question mark (`?`) at the end of every reply. Only ask a question if genuinely seeking clarification or starting a debate.
- **Natural Length Scaling**:
  - `pure_gif` / `emoji_reaction`: 0–20 characters.
  - `punchy_one_liner`: 20–70 characters.
  - `witty_sarcasm` / `casual_take`: 40–140 characters.
  - `in_depth_breakdown`: 120–260 characters.
- **Comment Reading**: Direct access to top 10 comments and likes to match the room vibe (banter, roast, hype, debate).

### 3.2 Dynamic Creation & Media Pipeline (`xbot/pipelines/trend_generator_pipeline.py`)

When consuming a `ResearchedTopic`:
1. **High Visual / Relatable Topic**: Route to `VisualEngine` to create a 4:5 vertical meme/infographic spec + short tension hook (<100 chars).
2. **Deep Research (>= 8 scraped posts)**: Route to `generate_thread`, attaching the top downloaded viral image to Tweet 1.
3. **A/B Debate Topic**: Route to `CreatePoll` with 2–4 options (24h duration).
4. **Fast News / Observation**: Synthesize a punchy 1–2 line standalone take with optional reaction GIF.

### 3.3 Browser Execution Engine (`xbot/browser/actions/x_actions.py`)

#### Native GIF Search Flow:
1. Locate GIF button: `button[aria-label="Add a GIF"]` or `[data-testid="gifSearchButton"]`.
2. Human-click GIF button.
3. Type `gif_query` with human delay into `input[data-testid="searchBox"]` or `input[placeholder*="Search GIFs"]`.
4. Wait for results container: `[data-testid="gifSearchResults"]` or `[data-testid="gifItem"]`.
5. Human-click first/second matching GIF item.
6. Type accompanying text (if any) and submit.

---

## 4. Verification & Testing Plan

### 4.1 Unit Tests
1. **`test_dynamic_reply_modes`**: Verify that `generate_sniper_reply` produces valid outputs across all 6 response modes (`pure_gif`, `emoji_reaction`, `punchy_one_liner`, `witty_sarcasm`, `casual_take`, `in_depth_breakdown`).
2. **`test_no_forced_question_mark`**: Ensure replies do NOT unconditionally end with `?`.
3. **`test_context_enrichment`**: Verify top 10 comments and image descriptions are formatted and included in prompt payloads.
4. **`test_trend_generator_format_matrix`**: Verify topic routing to 4:5 visual meme, thread with media, poll, or single take.
5. **`test_browser_gif_and_media_routing`**: Verify `execute_browser_action` routes `gif_query` and `media_paths` correctly to `ReplyToTweet`, `ComposePost`, and `ComposeThread`.

### 4.2 Integration Verification
1. Run full backend test suite (`pytest backend/tests/ -v`).
2. Verify live execution via `/pipelines/reply/trigger` and `/pipelines/trend_generator/trigger`.
