from __future__ import annotations
import hashlib
import logging
import textwrap
from pathlib import Path
from PIL import Image, ImageDraw
from xbot.ai.meme_renderer import (
    WIDTH, HEIGHT, BG_COLOR, CARD_BG, BORDER_COLOR, ACCENT_GREEN, TEXT_WHITE,
    TEXT_MUTED, _get_font, _ensure_output_dir, render_side_by_side, render_storyboard_4panel
)

logger = logging.getLogger(__name__)

def render_dark_infographic(
    title: str,
    bullet_points: list[str],
    stat_badge: str | None = None,
    output_path: str | None = None,
) -> str:
    """Renders a sleek, high-contrast dark infographic cheat-sheet."""
    img = Image.new("RGB", (WIDTH, HEIGHT), BG_COLOR)
    draw = ImageDraw.Draw(img)

    title_font = _get_font(46, bold=True)
    badge_font = _get_font(32, bold=True)
    point_font = _get_font(28, bold=False)
    footer_font = _get_font(20, bold=False)

    # Top Header Accent Bar
    draw.rectangle([(0, 0), (WIDTH, 12)], fill=ACCENT_GREEN)

    margin_x = 60
    draw.text((margin_x, 50), textwrap.fill(title, width=32), font=title_font, fill=TEXT_WHITE)

    # Stat Highlight Box (if provided)
    cur_y = 200
    if stat_badge:
        draw.rounded_rectangle([(margin_x, cur_y), (WIDTH - margin_x, cur_y + 110)], radius=16, fill=(18, 45, 30), outline=ACCENT_GREEN, width=2)
        draw.text((margin_x + 30, cur_y + 35), stat_badge, font=badge_font, fill=ACCENT_GREEN)
        cur_y += 150

    # Bullet point cards
    for idx, bp in enumerate(bullet_points[:5]):
        b_h = 160
        draw.rounded_rectangle([(margin_x, cur_y), (WIDTH - margin_x, cur_y + b_h)], radius=14, fill=CARD_BG, outline=BORDER_COLOR, width=1)
        # Bullet Number Circle
        draw.ellipse([(margin_x + 25, cur_y + 25), (margin_x + 75, cur_y + 75)], fill=(30, 41, 59))
        draw.text((margin_x + 42, cur_y + 36), str(idx + 1), font=badge_font, fill=TEXT_WHITE)

        # Bullet Text
        bp_wrap = textwrap.fill(bp, width=44)
        draw.text((margin_x + 100, cur_y + 30), bp_wrap, font=point_font, fill=TEXT_WHITE, spacing=8)
        cur_y += b_h + 30

    # Footer
    draw.text((margin_x, HEIGHT - 50), "XBot Pro • Cheat Sheet Series", font=footer_font, fill=TEXT_MUTED)

    if not output_path:
        out_dir = _ensure_output_dir()
        file_hash = hashlib.md5((title + "".join(bullet_points)).encode()).hexdigest()[:10]
        output_path = str(out_dir / f"infographic_{file_hash}.png")

    img.save(output_path, "PNG", quality=95)
    logger.info("Rendered dark infographic at: %s", output_path)
    return output_path


def render_meme_from_spec(spec_data: dict[str, Any], output_path: str | None = None) -> str:
    """
    Dispatches to the appropriate renderer based on format_type in the VisualPostSpec.
    """
    fmt = spec_data.get("format_type", "storyboard_4panel")
    copy_text = spec_data.get("tweet_copy", "")
    topic = spec_data.get("target_simcluster", "Tech")

    if fmt == "side_by_side":
        return render_side_by_side(
            title=f"Expectation vs Reality: {topic}",
            left_header="Theory / Expectation",
            left_content="Clean flow
Zero latency
Perfect schema",
            right_header="Reality / Live Prod",
            right_content=copy_text or "Timeout cascade
Edge case storm
Hotfix deployed",
            output_path=output_path,
        )
    elif fmt == "dark_infographic":
        points = [
            copy_text or "Core operational architecture",
            "High-velocity pipeline execution",
            "Sub-second decision engine latency",
            "Zero-hallucination fact grounding",
        ]
        return render_dark_infographic(
            title=f"Architecture: {topic}",
            bullet_points=points,
            stat_badge="99.9% Uptime Verified",
            output_path=output_path,
        )
    else:  # storyboard_4panel / default
        return render_storyboard_4panel(
            title=copy_text[:60] if copy_text else f"The 4 Stages of {topic}",
            output_path=output_path,
        )
