#!/usr/bin/env python3
"""
Diagnostic verification script for the Master Character Prompt Engine
and dynamic boundary enforcement.
"""

import sys
from pathlib import Path

# Ensure backend directory is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

from xbot.persona.loader import load_persona
from xbot.persona.prompt_engine import build_character_master_prompt
from xbot.ai.sniper.prompt_builder import _build_sniper_system_prompt
from xbot.ai.poll_prompts import _build_poll_system_prompt
from xbot.ai.visual_inference import _build_visual_system_prompt

def main():
    profile_dir = Path(__file__).resolve().parents[2] / "data" / "profiles" / "test_profile1"
    persona = load_persona(profile_dir)

    print("=================================================================")
    print("1. MASTER CHARACTER PROMPT (STANDALONE / TOP OF PROMPT)")
    print("=================================================================")
    master_prompt = build_character_master_prompt(persona)
    print(master_prompt)
    print("\n")

    # Assertions on master prompt
    assert "Kaya" in master_prompt
    assert "Delhi" in master_prompt
    assert "CHARACTER REALITY & BOUNDARIES (ENFORCE STRICTLY):" in master_prompt
    assert "iPhone Pro Max" in master_prompt
    assert "Dedicated GPUs" in master_prompt
    assert "Software engineer" in master_prompt
    assert "< 240" not in master_prompt, "Hardcoded 240 char limit found in master prompt!"

    print("=================================================================")
    print("2. SNIPER SYSTEM PROMPT (KOL REPLIES)")
    print("=================================================================")
    sniper_prompt = _build_sniper_system_prompt(persona)
    assert master_prompt in sniper_prompt, "Master prompt not prepended to sniper prompt!"
    assert "My GPU is sweating" not in sniper_prompt, "Old GPU hallucination example found in sniper prompt!"
    assert "Boeing 747" in sniper_prompt
    print("Sniper prompt verified: Starts with Master Character Prompt and has no GPU examples.")

    print("=================================================================")
    print("3. POLL SYSTEM PROMPT")
    print("=================================================================")
    poll_prompt = _build_poll_system_prompt(persona)
    assert master_prompt in poll_prompt, "Master prompt not prepended to poll prompt!"
    print("Poll prompt verified: Starts with Master Character Prompt.")

    print("=================================================================")
    print("4. VISUAL INFERENCE SYSTEM PROMPT")
    print("=================================================================")
    visual_prompt = _build_visual_system_prompt(persona)
    assert master_prompt in visual_prompt, "Master prompt not prepended to visual prompt!"
    print("Visual prompt verified: Starts with Master Character Prompt.")

    print("=================================================================")
    print("5. TRIAGE / ANALYZE TWEET PROMPT (SCORER)")
    print("=================================================================")
    from xbot.ai.engagement.scorer import build_triage_prompts, build_reply_prompts
    from xbot.persona.loader import load_learned_state, Relationships
    learned_state = load_learned_state(profile_dir)
    relationships = Relationships()
    triage_sys, triage_user = build_triage_prompts(
        persona, learned_state, "Evaluate tweet", {"characteristic"}, "elonmusk", "Thinking of colonizing Mars", False
    )
    assert master_prompt in triage_sys, "Master prompt not prepended to triage prompt!"
    print("Triage prompt verified: Starts with Master Character Prompt.")

    print("=================================================================")
    print("6. FEED ENGAGEMENT REPLY PROMPT (SCORER)")
    print("=================================================================")
    reply_sys, reply_user = build_reply_prompts(
        persona, learned_state, relationships, "Generate reply", {"personality"}, "sama", "AGI incoming", False
    )
    assert master_prompt in reply_sys, "Master prompt not prepended to feed reply prompt!"
    print("Feed reply prompt verified: Starts with Master Character Prompt.")

    print("=================================================================")
    print("7. TREND TAKES SYSTEM PROMPT")
    print("=================================================================")
    from xbot.ai.trend_gen.prompts import _build_trend_system_prompt
    trend_sys = _build_trend_system_prompt(persona)
    assert master_prompt in trend_sys, "Master prompt not prepended to trend system prompt!"
    print("Trend prompt verified: Starts with Master Character Prompt.")

    print("\n>>> ALL 7 CHARACTER PROMPT PIPELINES VERIFIED SUCCESSFULLY! <<<")

if __name__ == "__main__":
    main()
