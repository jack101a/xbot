from __future__ import annotations
from typing import Literal

FORMAT_TYPES = Literal["storyboard_4panel", "side_by_side", "urban_lifestyle", "dark_infographic"]
SIMCLUSTERS = Literal["Tech/AI", "Cinema/Prestige", "Urban/Creator", "Anime/PopCulture"]

VISUAL_FORMAT_TEMPLATES: dict[str, dict[str, str]] = {
    "storyboard_4panel": {
        "name": "4-Panel Storyboard / Progression Comic",
        "description": "Sequential 4-panel visual comic or scenario progression in 4:5 portrait (1080x1350). High contrast, clean panel borders, escalating tension in panels 1-3 with humorous or insightful resolution in panel 4.",
        "default_simcluster": "Tech/AI",
        "prompt_template": (
            "A detailed 4-panel comic storyboard grid in 4:5 vertical portrait aspect ratio (1080x1350). "
            "Panel 1: [Setup], Panel 2: [Escalation], Panel 3: [Peak Tension], Panel 4: [Visual Punchline/Payoff]. "
            "High-contrast dark-mode palette (#0D1117 background), crisp clean panel dividers, expressive cinematic lighting, "
            "digital illustration style with refined linework, zero distorted AI text or artifacts. --ar 4:5"
        ),
    },
    "side_by_side": {
        "name": "Side-by-Side Comparison / Expectation vs Reality",
        "description": "2-panel vertical split comparison in 4:5 portrait (1080x1350). Left/Top: Expectation / Ideal / Legacy. Right/Bottom: Reality / Actual / Modern. Stark visual contrast and bold minimalist typography.",
        "default_simcluster": "Tech/AI",
        "prompt_template": (
            "A split side-by-side visual comparison in 4:5 vertical portrait aspect ratio (1080x1350). "
            "Left side: [Expectation / Legacy / Theory], soft serene lighting. "
            "Right side: [Reality / Modern / Production], dramatic high-contrast moody lighting. "
            "Bold minimalist typography labels, sharp render, ultra-detailed textures, zero blurry AI distortions. --ar 4:5"
        ),
    },
    "urban_lifestyle": {
        "name": "Candid Urban Creator Realism / 35mm Film",
        "description": "Authentic raw 35mm film photography in 4:5 portrait (1080x1350). South Asian creator aesthetic, candid realism, Kodak Portra 400 warm palette, natural ambient lighting, subtle film grain, anti-plastic authenticity.",
        "default_simcluster": "Urban/Creator",
        "prompt_template": (
            "Candid 35mm film photograph in 4:5 vertical portrait aspect ratio (1080x1350), shot on Leica M6 with 35mm f/1.4 lens on Kodak Portra 400 film. "
            "A stylish young South Asian creator in an urban studio cafe in Mumbai surrounded by camera gear and laptop, caught in a genuine candid expression. "
            "Soft natural golden-hour ambient lighting, rich warm color grading, organic film grain, authentic skin textures with subtle imperfections, no glossy AI plastic smoothing. --ar 4:5"
        ),
    },
    "dark_infographic": {
        "name": "High-Contrast Dark-Mode Cheat Sheet & System Architecture",
        "description": "Sleek high-contrast dark-mode infographic / cheatsheet in 4:5 portrait (1080x1350). Background #0D1117, neon cyan (#58A6FF) and electric amber (#F2994A) accents, monospace terminal aesthetic, modular architecture diagram.",
        "default_simcluster": "Tech/AI",
        "prompt_template": (
            "A clean, high-contrast dark-mode technical infographic and system diagram in 4:5 vertical portrait aspect ratio (1080x1350). "
            "Deep dark slate background (#0D1117), crisp vector diagrams with neon cyan (#58A6FF) and warm amber (#F2994A) signal paths. "
            "Modular architecture boxes, clean monospace typography, structured layout with high legibility on mobile screens, ultra-sharp vector graphics, zero visual clutter. --ar 4:5"
        ),
    },
}

