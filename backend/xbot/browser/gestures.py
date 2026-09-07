from __future__ import annotations
import asyncio
import math
import random
from typing import Tuple
from playwright.async_api import Page

def _bezier_curve_points(
    p0: Tuple[float, float],
    p1: Tuple[float, float],
    p2: Tuple[float, float],
    p3: Tuple[float, float],
    steps: int,
) -> list[Tuple[float, float]]:
    """
    Generate points along a cubic Bezier curve.
    p0 = start, p1/p2 = control points, p3 = end.
    This creates natural acceleration/deceleration mouse paths.
    """
    points = []
    for i in range(steps + 1):
        t = i / steps
        # Standard cubic Bezier formula
        x = (
            (1 - t) ** 3 * p0[0]
            + 3 * (1 - t) ** 2 * t * p1[0]
            + 3 * (1 - t) * t ** 2 * p2[0]
            + t ** 3 * p3[0]
        )
        y = (
            (1 - t) ** 3 * p0[1]
            + 3 * (1 - t) ** 2 * t * p1[1]
            + 3 * (1 - t) * t ** 2 * p2[1]
            + t ** 3 * p3[1]
        )
        # Add micro-jitter to each point (±2px), like hand tremor
        x += random.uniform(-1.5, 1.5)
        y += random.uniform(-1.5, 1.5)
        points.append((x, y))
    return points


async def human_mouse_move(
    page: Page,
    target_x: float,
    target_y: float,
    current_x: float | None = None,
    current_y: float | None = None,
) -> None:
    """
    Moves the mouse from the current position to (target_x, target_y)
    using a randomized cubic Bezier path, simulating natural human
    hand movement with acceleration and small jitter.
    """
    if current_x is None:
        current_x = random.uniform(100, 700)
    if current_y is None:
        current_y = random.uniform(100, 500)

    # Distance-proportional step count (more steps = smoother for longer distances)
    distance = math.hypot(target_x - current_x, target_y - current_y)
    steps = max(8, min(40, int(distance / 15)))

    # Randomize control points to produce natural curved arcs
    mid_x = (current_x + target_x) / 2
    mid_y = (current_y + target_y) / 2
    cp1 = (
        mid_x + random.uniform(-80, 80),
        mid_y + random.uniform(-80, 80),
    )
    cp2 = (
        mid_x + random.uniform(-60, 60),
        mid_y + random.uniform(-60, 60),
    )

    curve = _bezier_curve_points(
        (current_x, current_y), cp1, cp2, (target_x, target_y), steps
    )

    for pt in curve:
        await page.mouse.move(pt[0], pt[1])
        # Variable inter-step delay: slower at start/end (ease in/out), faster in middle
        await asyncio.sleep(random.uniform(0.004, 0.018))


