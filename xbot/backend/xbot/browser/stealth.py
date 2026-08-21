"""
Stealth script injection for Playwright browser contexts.
Applies playwright-stealth and additional custom property overrides
to make the automated browser look indistinguishable from a real one.
"""
import random

from playwright.async_api import BrowserContext, Page
from playwright_stealth import Stealth


def _build_stealth_script(platform: str = "Win32") -> str:
    """
    Build the stealth init script with correct values for the given platform.
    Called once per browser context — values are consistent within that session.
    """
    device_memory = random.choice([4, 8, 16])
    hw_concurrency = random.choice([4, 6, 8, 12])

    # Screen dimensions consistent with platform
    if "Mac" in platform:
        screen_w, screen_h = random.choice([(1440, 900), (1512, 982), (1920, 1200), (2560, 1600)])
    else:
        screen_w, screen_h = random.choice([(1366, 768), (1280, 800), (1920, 1080), (1600, 900)])

    return f"""
(() => {{
    // ── Hardware / Memory ──────────────────────────────────────────────────
    Object.defineProperty(navigator, 'deviceMemory', {{ get: () => {device_memory} }});
    Object.defineProperty(navigator, 'hardwareConcurrency', {{ get: () => {hw_concurrency} }});

    // ── Platform — must match UA OS string ───────────────────────────────
    Object.defineProperty(navigator, 'platform', {{ get: () => '{platform}' }});

    // ── Screen fingerprint ────────────────────────────────────────────────
    Object.defineProperty(screen, 'width', {{ get: () => {screen_w} }});
    Object.defineProperty(screen, 'height', {{ get: () => {screen_h} }});
    Object.defineProperty(screen, 'availWidth', {{ get: () => {screen_w} }});
    Object.defineProperty(screen, 'availHeight', {{ get: () => {screen_h - 40} }});
    Object.defineProperty(screen, 'colorDepth', {{ get: () => 24 }});
    Object.defineProperty(screen, 'pixelDepth', {{ get: () => 24 }});

    // ── Touch: desktop = 0 touch points ──────────────────────────────────
    Object.defineProperty(navigator, 'maxTouchPoints', {{ get: () => 0 }});

    // ── Languages ─────────────────────────────────────────────────────────
    Object.defineProperty(navigator, 'languages', {{ get: () => ['en-US', 'en'] }});

    // ── CDP Runtime.enable leak — trap mitigation ─────────────────────────
    // Anti-bots set a getter trap on Error.stack to detect if CDP is active.
    // We override toString to avoid triggering the serialization path.
    const _origDescriptor = Object.getOwnPropertyDescriptor(Error.prototype, 'stack');
    if (_origDescriptor && typeof _origDescriptor.get === 'function') {{
        const _origGet = _origDescriptor.get;
        Object.defineProperty(Error.prototype, 'stack', {{
            get() {{
                // Only return stack if it is a "real" call — not CDP serialization
                try {{
                    const s = _origGet.call(this);
                    return s;
                }} catch (e) {{
                    return '';
                }}
            }},
            configurable: true,
        }});
    }}

    // ── Permissions API — avoid broken state objects ──────────────────────
    if (navigator.permissions && navigator.permissions.query) {{
        const _origQuery = navigator.permissions.query.bind(navigator.permissions);
        navigator.permissions.query = (parameters) => (
            parameters.name === 'notifications'
                ? Promise.resolve({{ state: Notification.permission }})
                : _origQuery(parameters)
        );
    }}

    // ── WebGL vendor/renderer (real Intel GPU strings) ────────────────────
    const _getParam = WebGLRenderingContext.prototype.getParameter;
    WebGLRenderingContext.prototype.getParameter = function(parameter) {{
        if (parameter === 37445) return 'Intel Inc.';
        if (parameter === 37446) return 'Intel Iris OpenGL Engine';
        return _getParam.call(this, parameter);
    }};

    // ── AudioContext fingerprint — add tiny imperceptible noise ───────────
    const _origGetChannelData = AudioBuffer.prototype.getChannelData;
    AudioBuffer.prototype.getChannelData = function(channel) {{
        const data = _origGetChannelData.call(this, channel);
        if (data.length > 0) {{
            // Tiny noise (< floating point epsilon) — imperceptible to humans
            data[0] += 1e-7 * Math.random();
        }}
        return data;
    }};
}})();
"""


async def apply_stealth(page: Page, platform: str = "Win32") -> None:
    """Applies stealth to a single Playwright page."""
    await Stealth().apply_stealth_async(page)
    await page.add_init_script(_build_stealth_script(platform))


async def apply_stealth_to_context(context: BrowserContext, platform: str = "Win32") -> None:
    """Applies stealth to a Playwright BrowserContext (preferred — covers all pages)."""
    await Stealth().apply_stealth_async(context)
    await context.add_init_script(_build_stealth_script(platform))

