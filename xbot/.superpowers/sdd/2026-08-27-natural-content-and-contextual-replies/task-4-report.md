# Task 4 Report: Dynamic Trend Generator (4:5 Memes, Media Threads, Polls, Hot Takes)

## Overview
Successfully implemented Task 4 of the natural content & contextual replies specification for XBot Pro. Upgraded `backend/xbot/pipelines/trend_generator_pipeline.py` and unit test suite `backend/tests/test_trend_generator_pipeline.py` to route consumed `ResearchedTopic` records through an autonomous 4-way creation decision matrix based on topic depth, category, media assets, and keyword semantics.

---

## Deliverables & Implementation Details

### 1. Dynamic 4-Way Creation Decision Matrix (`determine_creation_format`)
Implemented `determine_creation_format(topic: ResearchedTopic, persona: Persona | None = None) -> str` evaluating the topic signals into one of four creation modalities:

1. **4:5 Vertical Meme / Visual Infographic (`VisualEngine`)**:
   - **Trigger Criteria**: High visual, humor, comic, cheatsheet, diagram, or lifestyle appeal (keywords: `meme`, `comic`, `storyboard`, `infographic`, `cheatsheet`, `system design`, `system architecture`, `lifestyle`, `photo`, `cinema`, `nolan`, `relatable`, `expectation vs reality`, `side by side`, `bts`, `4-panel`, `4:5`, etc.) or `topic.source == "visual"`.
   - **Generation**: Calls `generate_visual_post_spec(topic=topic.topic, persona=persona)`.
   - **Staging**: Staged as `ContentType.POST` with `status=ContentStatus.APPROVED`.
   - **AI Metadata**: Stored with `visual_post_spec`, `format_type`, `aspect_ratio="4:5"`, `target_simcluster`, `one_two_punch_strategy`, `image_prompt`, and `media_paths`.
   - **Content Body**: Punchy tension hook (<100 chars).

2. **Rich Deep-Dive Thread (`generate_thread`)**:
   - **Trigger Criteria**: Deep research (`>= 8` scraped posts and long topic name `> 30` chars, or deep-dive keywords like `deep dive`, `in-depth breakdown`, `mega thread`, `complete guide`).
   - **Generation**: Calls `generate_thread(topic=topic.topic, persona=persona, num_tweets=4, deep_research=False, profile_slug=profile_slug)`.
   - **Staging**: Staged as `ContentType.THREAD` with `status=ContentStatus.APPROVED`.
   - **Media Attachment**: Attaches top downloaded viral media from research (`topic.media_paths[0]`) to Tweet 1 (`ThreadItem(position=0, item_type="hook", media_url=...)`).
   - **Thread Items**: Stored as individual `ThreadItem` records linked to the parent `Content` item with positions 0 to N-1.

3. **Interactive Community Poll (`generate_poll`)**:
   - **Trigger Criteria**: Polarizing A/B dilemmas, tool/framework comparisons, or preference choices (keywords: ` vs `, ` vs. `, `versus`, ` or `, `which `, `choose`, `poll`, `debate`, `prefer`, `which is better`, `what's better`, `pick one`, `dilemma`, `would you rather`, `ranking`).
   - **Generation**: Calls `generate_poll(persona=persona, topic=topic.topic)`.
   - **Staging**: Staged as `ContentType.POLL` with `status=ContentStatus.APPROVED`.
   - **AI Metadata**: Stored with `poll`, `poll_options` (2–4 options, each <= 25 chars), `duration_days=1` (24h duration), `context_hook`, and `reasoning`.
   - **Content Body**: Question and formatted options.

4. **Punchy Standalone Hot Take (`synthesize_creator_post`)**:
   - **Trigger Criteria**: Fast news, sharp takes, industry observations (default / general news branch).
   - **Generation**: Calls `synthesize_creator_post(topic=topic.topic, persona=persona, image_url=media_paths[0] if present)`.
   - **Optimization**: Passes through `AntiAIGatekeeper`, `Dynamic Formatting Engine`, and `optimize_post_for_virality`.
   - **Link Extraction & Reaction GIF**: Extracts URLs into `first_reply_text` and detects optional reaction `gif_query` for reactive / emotional takes.
   - **Staging**: Staged as `ContentType.POST` with `status=ContentStatus.APPROVED`.

---

## Test Suite & Verification

### Unit Test Suite (`backend/tests/test_trend_generator_pipeline.py`)
- `test_determine_creation_format_matrix`: Verified routing for memes, infographics, deep research threads, A/B polls, and standalone hot takes.
- `test_generate_content_for_topic_visual_meme`: Verified visual 4:5 aspect ratio spec generation, tension hook length (<140 chars), and metadata persistence.
- `test_generate_content_for_topic_deep_dive_thread_with_media`: Verified 4-tweet thread generation, `ThreadItem` records creation, and viral media attachment to Tweet 1.
- `test_generate_content_for_topic_interactive_poll`: Verified 2-4 option poll generation, 24h duration, and poll metadata storage.
- `test_generate_content_for_topic_standalone_hot_take`: Verified creator post synthesis, link extraction for 1st reply, and virality optimization.
- `test_run_trend_generator_for_profile_processes_pending`: Verified profile batch processing across pending researched topics.

### Full Pipeline Test Suite Results
Command: `pytest backend/tests/test_trend_generator_pipeline.py backend/tests/test_trend_researcher_pipeline.py backend/tests/test_visual_engine.py backend/tests/test_thread_generator.py -v`
- **Result**: **25 passed in 5.40s** (100% passing)

---

## Git Commit Details
- **Commit**: `28c6e32`
- **Message**: `feat(pipeline): implement dynamic 4-way creation matrix in trend generator pipeline`
- **Files**:
  - `backend/xbot/pipelines/trend_generator_pipeline.py`
  - `backend/tests/test_trend_generator_pipeline.py`
  - `backend/xbot/models/content.py`
