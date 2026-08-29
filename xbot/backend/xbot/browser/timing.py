"""
Human-like timing and interaction primitives for the Playwright browser automation layer.

All functions in this module are designed to closely mimic real human biological
patterns: variable pacing, Bezier-curve mouse trajectories, inertia-based scrolling,
hover-before-click, and natural cognitive "think time" pauses.
"""
from __future__ import annotations

import asyncio
import math
import random
from typing import Tuple

from playwright.async_api import ElementHandle, Page


# ---------------------------------------------------------------------------
# Low-level timing helpers
# ---------------------------------------------------------------------------

async def sleep_with_jitter(base_delay_ms: float) -> None:
    """
    Sleeps for a duration based on a base delay in milliseconds, adding
    bounded jitter (-30% to +50%) to mimic human variance.
    """
    jitter_factor = random.uniform(-0.3, 0.5)
    final_delay_ms = base_delay_ms * (1.0 + jitter_factor)
    final_delay_seconds = max(0.1, final_delay_ms / 1000.0)
    await asyncio.sleep(final_delay_seconds)


async def sleep_think_time(min_ms: float = 1000.0, max_ms: float = 5000.0) -> None:
    """
    Simulates a cognitive "thinking" pause before a decision action.
    Humans vary widely before clicking — capture that with a wide random range.
    """
    delay_seconds = random.uniform(min_ms, max_ms) / 1000.0
    await asyncio.sleep(delay_seconds)


async def sleep_micro(min_ms: float = 30.0, max_ms: float = 120.0) -> None:
    """Very short micro-pause — used between tiny interactions."""
    await asyncio.sleep(random.uniform(min_ms, max_ms) / 1000.0)


# ---------------------------------------------------------------------------
# Mouse trajectory simulation
# ---------------------------------------------------------------------------

from xbot.browser.gestures import (
    _bezier_curve_points,
    human_mouse_move,
)

async def human_click(
    page: Page,
    element: ElementHandle,
    hover_pause_ms_min: float = 300.0,
    hover_pause_ms_max: float = 900.0,
) -> None:
    """
    Performs a human-like click:
    1. Scroll element into view.
    2. Move mouse to element via Bezier path.
    3. Hover/pause (as if reading the button label).
    4. Click with a small offset from center.
    """
    # Scroll element into view with safe timeout
    try:
        await element.scroll_into_view_if_needed(timeout=2500)
    except Exception:
        pass
    await sleep_micro(80, 200)

    # Get element bounding box
    box = await element.bounding_box()
    if box is None:
        # Fallback to simple click if we can't get position
        try:
            await element.click(timeout=4000)
        except Exception:
            pass
        return

    # Target a slightly randomized point inside the element (not always dead-center)
    target_x = box["x"] + box["width"] * random.uniform(0.2, 0.8)
    target_y = box["y"] + box["height"] * random.uniform(0.2, 0.8)

    # Move mouse using Bezier curve
    await human_mouse_move(page, target_x, target_y)

    # Hover pause — simulates reading/noticing the element
    await sleep_think_time(hover_pause_ms_min, hover_pause_ms_max)

    # Dispatch click to element
    try:
        await element.click()
    except Exception:
        click_x = target_x + random.uniform(-3, 3)
        click_y = target_y + random.uniform(-3, 3)
        await page.mouse.click(click_x, click_y)

    await sleep_micro(50, 150)


async def human_click_selector(
    page: Page,
    selector: str,
    hover_pause_ms_min: float = 300.0,
    hover_pause_ms_max: float = 900.0,
) -> None:
    """
    Convenience wrapper for human_click that accepts a CSS selector.
    """
    element = await page.wait_for_selector(selector, timeout=8000)
    if element:
        await human_click(page, element, hover_pause_ms_min, hover_pause_ms_max)
    else:
        # Fallback
        await page.click(selector)


# ---------------------------------------------------------------------------
# Inertia-based scrolling
# ---------------------------------------------------------------------------

async def human_scroll(
    page: Page,
    pixels: int,
    direction: str = "down",
    inertia_steps: int | None = None,
) -> None:
    """
    Scrolls using a human-like inertia model:
    - Starts slow (ease-in), accelerates, then decelerates (ease-out).
    - Adds micro-jitter between steps.
    - Simulates the "flick" pattern real users use on a trackpad/mouse wheel.

    Args:
        page: Playwright page object.
        pixels: Total pixels to scroll.
        direction: 'down' or 'up'.
        inertia_steps: Number of steps (auto-calculated if None).
    """
    if inertia_steps is None:
        inertia_steps = max(4, min(15, pixels // 80))

    sign = 1 if direction == "down" else -1

    # Generate step sizes using sine easing (slow-fast-slow)
    step_sizes = []
    for i in range(inertia_steps):
        t = i / (inertia_steps - 1) if inertia_steps > 1 else 1.0
        # Sine ease-in-out
        ease = math.sin(t * math.pi)
        step_sizes.append(ease)

    # Normalize so total equals requested pixels
    total_ease = sum(step_sizes) or 1.0
    step_sizes = [s / total_ease * pixels for s in step_sizes]

    for step_px in step_sizes:
        jitter = random.uniform(-8, 8)
        actual_px = sign * (step_px + jitter)
        await page.evaluate(f"window.scrollBy(0, {actual_px})")
        await asyncio.sleep(random.uniform(0.03, 0.1))

    # Tiny settle pause after scroll completes
    await sleep_micro(200, 500)


async def human_scroll_to_element(page: Page, element: ElementHandle) -> None:
    """Scrolls an element into view then adds a natural read pause."""
    try:
        await element.scroll_into_view_if_needed(timeout=2500)
    except Exception:
        pass
    await sleep_think_time(400, 1200)


# ---------------------------------------------------------------------------
# Human typing (unchanged from previous implementation + improvements)
# ---------------------------------------------------------------------------

async def human_type(
    page: Page, selector: str, text: str, typo_chance: float = 0.04
) -> None:
    """
    Types text into a focused input element character-by-character,
    adding variable key delays and simulating typos and backspaces.
    """
    element = await page.wait_for_selector(selector, timeout=8000)
    if element:
        try:
            await element.focus()
        except Exception:
            pass
        await human_click(page, element, 200, 500)
    else:
        await page.focus(selector)

    await sleep_with_jitter(400)  # Pause slightly before starting to type

    for i, char in enumerate(text):
        # Occasional short "think" pause mid-sentence (3% chance)
        if i > 0 and random.random() < 0.03:
            await sleep_think_time(400, 1200)

        # Check if we should simulate a typo on alphabetic characters
        if random.random() < typo_chance and char.isalpha():
            wrong_char = random.choice("abcdefghijklmnopqrstuvwxyz")
            if wrong_char != char.lower():
                await page.keyboard.type(wrong_char)
                await asyncio.sleep(random.uniform(0.08, 0.25))  # Realization pause
                await page.keyboard.press("Backspace")
                await asyncio.sleep(random.uniform(0.05, 0.15))  # Recovery pause

        # Type the correct character
        await page.keyboard.type(char)

        # Variable inter-key delay — slightly slower for punctuation/space
        if char in " .,!?;:":
            await asyncio.sleep(random.uniform(0.08, 0.18))
        else:
            await asyncio.sleep(random.uniform(0.04, 0.13))

    await sleep_with_jitter(600)  # Post-typing pause
