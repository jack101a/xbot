"""
Autonomous 4:5 Vertical Meme & Visual Infographic Renderer for XBot Pro.
Renders mobile viewport takeover graphics (1080x1350, 4:5 aspect ratio)
with clean dark mode palettes, vibrant borders, and high readability.
"""

from __future__ import annotations

import hashlib
import logging
import os
import textwrap
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)

# Default canvas dimensions: 4:5 Vertical Portrait (1080x1350)
WIDTH = 1080
HEIGHT = 1350

# Color Palette (Deep dark-mode with high contrast accents)
BG_COLOR = (13, 17, 23)        # #0D1117 Github dark
CARD_BG = (22, 27, 34)         # #161B22 Elevated card
LEFT_CARD_BG = (26, 32, 44)    # Left panel card
RIGHT_CARD_BG = (35, 20, 26)   # Right panel card (subtle rose tint)
BORDER_COLOR = (48, 54, 61)    # #30363D Border
ACCENT_CYAN = (56, 189, 248)   # #38BDF8 Sky cyan
ACCENT_PURPLE = (168, 85, 247) # #A855F7 Vibrant purple
ACCENT_ROSE = (244, 63, 94)    # #F43F5E Coral rose
ACCENT_GREEN = (34, 197, 94)   # #22C55E Emerald
TEXT_WHITE = (240, 246, 252)   # #F0F6FC High contrast text
TEXT_MUTED = (139, 148, 158)   # #8B949E Subtitle text


def _get_font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    """Tries loading standard system TTF fonts, falling back to default."""
    font_candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf" if bold else "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]
    for p in font_candidates:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                pass
    return ImageFont.load_default()


def _ensure_output_dir(target_dir: str = "data/generated_media") -> Path:
    out = Path(target_dir)
    out.mkdir(parents=True, exist_ok=True)
    return out


def render_side_by_side(
    title: str,
    left_header: str = "Expectation / Theory",
    left_content: str = "Clean documentation\nPerfect unit tests\nPredictable deployments",
    right_header: str = "Reality / Production",
    right_content: str = "Hotfixes in prod at 3 AM\nUndefined is not a function\nNobody knows who wrote the query",
    output_path: str | None = None,
) -> str:
    """Renders a 4:5 vertical Side-by-Side comparison graphic."""
    img = Image.new("RGB", (WIDTH, HEIGHT), BG_COLOR)
    draw = ImageDraw.Draw(img)

    title_font = _get_font(46, bold=True)
    header_font = _get_font(32, bold=True)
    body_font = _get_font(28, bold=False)
    footer_font = _get_font(20, bold=False)

    # Top Header Accent Bar
    draw.rectangle([(0, 0), (WIDTH, 12)], fill=ACCENT_CYAN)

    # Title
    margin_x = 60
    title_wrapped = textwrap.fill(title, width=32)
    draw.text((margin_x, 60), title_wrapped, font=title_font, fill=TEXT_WHITE)

    # Card Dimensions
    card_top = 220
    card_h = 480
    card_w = WIDTH - (margin_x * 2)

    # Top / Left Card (Expectation)
    draw.rounded_rectangle([(margin_x, card_top), (margin_x + card_w, card_top + card_h)], radius=20, fill=CARD_BG, outline=ACCENT_CYAN, width=2)
    draw.rounded_rectangle([(margin_x + 24, card_top + 24), (margin_x + 360, card_top + 70)], radius=10, fill=(14, 40, 60))
    draw.text((margin_x + 40, card_top + 32), left_header.upper(), font=header_font, fill=ACCENT_CYAN)
    
    left_lines = textwrap.fill(left_content, width=38)
    draw.text((margin_x + 35, card_top + 100), left_lines, font=body_font, fill=TEXT_WHITE, spacing=14)

    # Bottom / Right Card (Reality)
    card2_top = card_top + card_h + 40
    draw.rounded_rectangle([(margin_x, card2_top), (margin_x + card_w, card2_top + card_h)], radius=20, fill=RIGHT_CARD_BG, outline=ACCENT_ROSE, width=2)
    draw.rounded_rectangle([(margin_x + 24, card2_top + 24), (margin_x + 340, card2_top + 70)], radius=10, fill=(60, 20, 30))
    draw.text((margin_x + 40, card2_top + 32), right_header.upper(), font=header_font, fill=ACCENT_ROSE)

    right_lines = textwrap.fill(right_content, width=38)
    draw.text((margin_x + 35, card2_top + 100), right_lines, font=body_font, fill=TEXT_WHITE, spacing=14)

    # Footer Branding
    draw.text((margin_x, HEIGHT - 50), "XBot Pro • Real-Time Growth Engine", font=footer_font, fill=TEXT_MUTED)

    if not output_path:
        out_dir = _ensure_output_dir()
        file_hash = hashlib.md5((title + left_content + right_content).encode()).hexdigest()[:10]
        output_path = str(out_dir / f"side_by_side_{file_hash}.png")

    img.save(output_path, "PNG", quality=95)
    logger.info("Rendered Side-by-Side graphic at: %s", output_path)
    return output_path


def render_4panel_storyboard(
    title: str,
    panels: list[str] | None = None,
    output_path: str | None = None,
) -> str:
    """Renders a 4:5 vertical 4-Panel progression comic/storyboard."""
    if not panels or len(panels) < 4:
        panels = [
            "Stage 1: 'This will take 10 minutes max.'",
            "Stage 2: Finding a strange runtime error in line 42.",
            "Stage 3: 14 browser tabs open, rewriting the whole module.",
            "Stage 4: Missing comma in config file.",
        ]

    img = Image.new("RGB", (WIDTH, HEIGHT), BG_COLOR)
    draw = ImageDraw.Draw(img)

    title_font = _get_font(44, bold=True)
    step_font = _get_font(26, bold=True)
    body_font = _get_font(26, bold=False)
    footer_font = _get_font(20, bold=False)

    # Top Header Accent Bar
    draw.rectangle([(0, 0), (WIDTH, 12)], fill=ACCENT_PURPLE)

    # Title
    margin_x = 60
    title_wrapped = textwrap.fill(title, width=32)
    draw.text((margin_x, 50), title_wrapped, font=title_font, fill=TEXT_WHITE)

    # 4 Panels Grid (2x2)
    p_w = 460
    p_h = 480
    gap = 40
    start_y = 200

    coords = [
        (margin_x, start_y),                          # Panel 1: Top-Left
        (margin_x + p_w + gap, start_y),              # Panel 2: Top-Right
        (margin_x, start_y + p_h + gap),              # Panel 3: Bottom-Left
        (margin_x + p_w + gap, start_y + p_h + gap),  # Panel 4: Bottom-Right
    ]

    colors = [ACCENT_CYAN, ACCENT_PURPLE, ACCENT_ROSE, ACCENT_GREEN]

    for idx, (x, y) in enumerate(coords):
        color = colors[idx % len(colors)]
        draw.rounded_rectangle([(x, y), (x + p_w, y + p_h)], radius=18, fill=CARD_BG, outline=color, width=2)
        # Step Badge
        draw.rounded_rectangle([(x + 18, y + 18), (x + 140, y + 60)], radius=8, fill=(30, 36, 46))
        draw.text((x + 28, y + 26), f"STEP {idx + 1}", font=step_font, fill=color)

        # Panel Text
        p_text = panels[idx]
        wrapped_p = textwrap.fill(p_text, width=24)
        draw.text((x + 22, y + 80), wrapped_p, font=body_font, fill=TEXT_WHITE, spacing=10)

    # Footer
    draw.text((margin_x, HEIGHT - 50), "XBot Pro • 4-Panel Breakdown", font=footer_font, fill=TEXT_MUTED)

    if not output_path:
        out_dir = _ensure_output_dir()
        file_hash = hashlib.md5((title + "".join(panels)).encode()).hexdigest()[:10]
        output_path = str(out_dir / f"storyboard_4panel_{file_hash}.png")

    img.save(output_path, "PNG", quality=95)
    logger.info("Rendered 4-Panel storyboard at: %s", output_path)
    return output_path



from xbot.ai.meme_infographic import (
    render_dark_infographic,
    render_meme_from_spec,
)

__all__ = [
    "WIDTH", "HEIGHT", "BG_COLOR", "CARD_BG", "BORDER_COLOR",
    "ACCENT_CYAN", "ACCENT_PURPLE", "ACCENT_ROSE", "ACCENT_GREEN",
    "TEXT_WHITE", "TEXT_MUTED", "_get_font", "_ensure_output_dir",
    "render_side_by_side", "render_storyboard_4panel",
    "render_dark_infographic", "render_meme_from_spec",
]
