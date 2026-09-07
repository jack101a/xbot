"""Cookie file parsing and validation for chatgpt-bridge.

Supports three on-disk formats, detected by CONTENT (not file extension):

* Netscape ``cookies.txt`` (tab-separated, ``#`` comments).
* A JSON array of cookie objects ``[{name, value, domain, path, expires, ...}]``.
* A Chrome-extension (Cookie-Editor style) wrapper object
  ``{"url": ..., "cookies": [...]}`` where each cookie may use
  ``expirationDate`` (float) and ``sameSite`` values like ``"lax"``,
  ``"no_restriction"``, ``"strict"``, or ``"unspecified"``.

All are normalized into Playwright-style cookie dicts.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

# The session cookie that proves a logged-in ChatGPT web session.
SESSION_COOKIE = "__Secure-next-auth.session-token"

# Defaults applied when a JSON cookie omits optional fields.
_DEFAULT_DOMAIN = "chatgpt.com"
_DEFAULT_PATH = "/"
_DEFAULT_EXPIRES = -1
_DEFAULT_SECURE = True
_DEFAULT_SAMESITE = "Lax"

# Map Chrome-extension sameSite values onto Playwright's canonical casing.
_SAMESITE_MAP = {
    "lax": "Lax",
    "strict": "Strict",
    "no_restriction": "None",
    "none": "None",
    "unspecified": "Lax",
}


class CookieFormatError(ValueError):
    """Raised when a cookie file cannot be parsed."""


def _normalize_json_cookie(raw: dict) -> dict:
    """Normalize a single JSON cookie dict into a Chromium-safe Playwright shape.

    Rules applied so ``context.add_cookies`` does not reject the cookie:

    * ``expires`` is coerced to ``int`` (Chromium rejects floats).
    * ``sameSite: "None"`` requires ``secure: true``; if the cookie is not
      secure, ``sameSite`` is downgraded to ``"Lax"``.
    * Host-only cookies (Chrome exports ``hostOnly: true`` with a domain that
      has no leading dot) are emitted in ``url`` form
      ``https://<domain><path>`` with the ``domain`` field dropped, which is
      the unambiguous way to set a host-only cookie in Playwright.
    """
    name = raw.get("name")
    value = raw.get("value")
    if not name or value is None:
        raise CookieFormatError(f"cookie missing name/value: {raw!r}")

    domain = raw.get("domain") or _DEFAULT_DOMAIN
    path = raw.get("path") or _DEFAULT_PATH
    host_only = bool(raw.get("hostOnly", False))

    # expires <- "expires" else "expirationDate" else -1; always int.
    expires = raw.get("expires")
    if expires is None:
        expires = raw.get("expirationDate")
    if expires is None:
        expires = _DEFAULT_EXPIRES
    expires = int(expires)

    secure = bool(raw.get("secure", _DEFAULT_SECURE))

    # Normalize sameSite casing; unknown/missing -> "Lax".
    same_site = raw.get("sameSite")
    if same_site is None:
        same_site = _DEFAULT_SAMESITE
    else:
        same_site = _SAMESITE_MAP.get(str(same_site).lower(), _DEFAULT_SAMESITE)

    # "None" requires secure; downgrade insecure "None" to "Lax".
    if same_site == "None" and not secure:
        same_site = "Lax"

    common = {
        "name": name,
        "value": value,
        "expires": expires,
        "secure": secure,
        "httpOnly": bool(raw.get("httpOnly", False)),
        "sameSite": same_site,
    }

    if host_only:
        # url-form host-only cookie; Playwright requires EITHER url OR
        # domain+path, not both — so drop domain AND path here.
        return {**common, "url": f"https://{domain}{path}"}

    if not domain.startswith("."):
        domain = "." + domain
    return {**common, "domain": domain, "path": path}


def _parse_json(text: str) -> list[dict]:
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise CookieFormatError(f"invalid JSON cookie file: {exc}") from exc

    if isinstance(data, list):
        cookies = data
    elif isinstance(data, dict) and isinstance(data.get("cookies"), list):
        # Chrome-extension wrapper object {"url": ..., "cookies": [...]}.
        cookies = data["cookies"]
    else:
        raise CookieFormatError(
            "JSON cookie file must be an array of cookies or a "
            '{"url": ..., "cookies": [...]} wrapper object'
        )

    return [_normalize_json_cookie(item) for item in cookies]


def _parse_netscape(text: str) -> list[dict]:
    """Parse a Netscape ``cookies.txt`` blob into Playwright-style cookies."""
    cookies: list[dict] = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        fields = stripped.split("\t")
        if len(fields) != 7:
            raise CookieFormatError(
                f"cookies.txt line {lineno}: expected 7 tab-separated fields, "
                f"got {len(fields)}"
            )
        domain, tailmatch, path, secure, expires, name, value = fields
        try:
            expires_int = int(expires)
        except ValueError as exc:
            raise CookieFormatError(
                f"cookies.txt line {lineno}: invalid expires value {expires!r}"
            ) from exc

        cookies.append(
            {
                "name": name,
                "value": value,
                "domain": domain,
                "path": path,
                "expires": expires_int,
                "secure": secure.lower() == "true",
                "httpOnly": False,
                "sameSite": _DEFAULT_SAMESITE,
            }
        )
    return cookies


def load_cookie_file(path: str | Path) -> list[dict]:
    """Load cookies from a Netscape or JSON cookie file.

    Format is detected by content: if the trimmed text starts with ``{`` or
    ``[`` it is parsed as JSON, otherwise as Netscape ``cookies.txt``.

    Returns a list of Playwright-style cookie dicts.
    """
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    stripped = text.lstrip()
    if stripped.startswith("{") or stripped.startswith("["):
        return _parse_json(text)
    return _parse_netscape(text)


def cookies_valid(cookies: list[dict]) -> bool:
    """Return True iff a valid, unexpired session-token cookie is present."""
    now = time.time()
    for c in cookies:
        if c.get("name") == SESSION_COOKIE:
            exp = c.get("expires", -1)
            if exp == -1 or exp > now:
                return True
    return False