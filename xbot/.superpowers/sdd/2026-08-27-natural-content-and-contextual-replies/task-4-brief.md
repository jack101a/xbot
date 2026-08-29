# Task 4 Brief: Dynamic Trend Generator (4:5 Memes, Media Threads, Polls, Hot Takes)

## Objective
Update `backend/xbot/pipelines/trend_generator_pipeline.py` to implement the autonomous 4-way creation decision matrix when consuming `ResearchedTopic`:
1. **4:5 Vertical Meme / Visual Infographic (`VisualEngine`)**:
   - Chosen when topic category/name/scraped tweets have high visual/humor/lifestyle appeal.
   - Generates 4:5 aspect ratio image prompt + short tension hook (<100 chars).
   - Staged as `ContentType.POST` with `ai_metadata={"visual_post_spec": visual_spec.model_dump(), "format_type": visual_spec.format_type, "aspect_ratio": "4:5"}`.
2. **Rich Deep-Dive Thread (`generate_thread`)**:
   - Chosen when topic has deep research (>= 8 scraped posts and long topic).
   - Tweet 1 attaches top downloaded viral media from research.
   - Staged as `ContentType.THREAD` with `ThreadItem` records.
3. **Interactive Community Poll (`CreatePoll`)**:
   - Chosen when topic involves an A/B polarizing dilemma or tool/framework comparison.
   - Staged as `ContentType.POLL` with 2–4 options (24h duration).
4. **Punchy Standalone Hot Take (`synthesize_creator_post`)**:
   - Chosen for fast news / sharp takes.
   - 1–2 punchy lines, optionally with reaction GIF query.
   - Staged as `ContentType.POST`.

## Files
- Modify: `backend/xbot/pipelines/trend_generator_pipeline.py`
- Test: `backend/tests/test_trend_generator_pipeline.py`

## Requirements & TDD Steps
1. Update `backend/tests/test_trend_generator_pipeline.py` to test all 4 branches:
   - Visual 4:5 meme creation.
   - Deep dive thread with media attachment.
   - Interactive poll creation.
   - Standalone punchy take.
2. Implement routing logic in `backend/xbot/pipelines/trend_generator_pipeline.py`.
3. Run `backend/.venv/bin/pytest backend/tests/test_trend_generator_pipeline.py -v`.
4. Run full pipeline test suite: `backend/.venv/bin/pytest backend/tests/test_trend_generator_pipeline.py backend/tests/test_trend_researcher_pipeline.py backend/tests/test_visual_engine.py backend/tests/test_thread_generator.py -v`.
5. Commit changes:
   `git add backend/xbot/pipelines/trend_generator_pipeline.py backend/tests/test_trend_generator_pipeline.py`
   `git commit -m "feat(pipeline): implement dynamic 4-way creation matrix in trend generator pipeline"`
6. Write report to `/home/ubuntu/projects/xbot/.superpowers/sdd/2026-08-27-natural-content-and-contextual-replies/task-4-report.md`.
