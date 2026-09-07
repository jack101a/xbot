from __future__ import annotations

import datetime
import json
import logging
import re
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def format_storage_state(
    auth_token: str,
    ct0: str,
    twid: str | None = None,
    expires_in_seconds: int = 365 * 24 * 3600,
) -> dict[str, Any]:
    """
    Generates a Playwright-compatible storageState dictionary containing cookies
    for both `.x.com` and `.twitter.com`.

    Sets:
    - auth_token: httpOnly=True, secure=True, sameSite="None"
    - ct0: httpOnly=False, secure=True, sameSite="Lax"
    - twid: httpOnly=False, secure=True, sameSite="None" (if provided)
    """
    expires = int(time.time()) + expires_in_seconds
    domains = [".x.com", ".twitter.com"]

    cookies: list[dict[str, Any]] = []

    for domain in domains:
        # auth_token cookie
        cookies.append({
            "name": "auth_token",
            "value": auth_token.strip(),
            "domain": domain,
            "path": "/",
            "expires": expires,
            "httpOnly": True,
            "secure": True,
            "sameSite": "None",
        })

        # ct0 cookie
        cookies.append({
            "name": "ct0",
            "value": ct0.strip(),
            "domain": domain,
            "path": "/",
            "expires": expires,
            "httpOnly": False,
            "secure": True,
            "sameSite": "Lax",
        })

        # twid cookie (optional)
        if twid and twid.strip():
            cookies.append({
                "name": "twid",
                "value": twid.strip(),
                "domain": domain,
                "path": "/",
                "expires": expires,
                "httpOnly": False,
                "secure": True,
                "sameSite": "None",
            })

    return {
        "cookies": cookies,
        "origins": [],
    }


def parse_cookie_string(raw: str) -> dict[str, str]:
    """
    Parses raw cookie inputs into a key-value dictionary.
    Supports:
    - Semicolon / comma / newline separated header strings: `auth_token=abc; ct0=def; twid=ghi`
    - Cookie header with prefix: `Cookie: auth_token=...`
    - JSON array (Cookie-Editor format): `[{"name": "auth_token", "value": "..."}, ...]`
    - JSON object: `{"auth_token": "...", "ct0": "..."}`
    - Playwright storageState JSON: `{"cookies": [{"name": "auth_token", "value": "..."}, ...]}`
    """
    if not raw or not raw.strip():
        return {}

    cleaned = raw.strip()

    # 1. Try parsing as JSON
    if cleaned.startswith(("{", "[")):
        try:
            parsed = json.loads(cleaned)
            if isinstance(parsed, list):
                result: dict[str, str] = {}
                for item in parsed:
                    if isinstance(item, dict) and "name" in item and "value" in item:
                        name = str(item["name"]).strip()
                        val = str(item["value"]).strip()
                        if name:
                            result[name] = val
                if result:
                    return result
            elif isinstance(parsed, dict):
                # Check for Playwright storage state format {"cookies": [...]}
                if "cookies" in parsed and isinstance(parsed["cookies"], list):
                    result = {}
                    for item in parsed["cookies"]:
                        if isinstance(item, dict) and "name" in item and "value" in item:
                            name = str(item["name"]).strip()
                            val = str(item["value"]).strip()
                            if name:
                                result[name] = val
                    if result:
                        return result
                else:
                    # Flat JSON object: {"auth_token": "...", "ct0": "..."}
                    result = {
                        str(k).strip(): str(v).strip()
                        for k, v in parsed.items()
                        if str(k).strip() and not isinstance(v, (dict, list))
                    }
                    if result:
                        return result
        except Exception:
            # Fall back to string parsing if JSON parsing fails
            pass

    # 2. String parsing
    # Strip leading "Cookie:" or "cookie:" header prefix if present
    if cleaned.lower().startswith("cookie:"):
        cleaned = cleaned[7:].strip()

    result: dict[str, str] = {}

    # Split by semicolon or newline
    segments = re.split(r"[;\r\n]+", cleaned)
    for seg in segments:
        seg = seg.strip()
        if not seg or "=" not in seg:
            continue
        key, val = seg.split("=", 1)
        key = key.strip()
        val = val.strip()
        # Remove surrounding quotes from value if present
        if len(val) >= 2 and (
            (val.startswith('"') and val.endswith('"'))
            or (val.startswith("'") and val.endswith("'"))
        ):
            val = val[1:-1]
        if key:
            result[key] = val

    return result


def inspect_profile_auth_status(profile_dir: Path | str) -> dict[str, Any]:
    """
    Inspects `profile_dir / "storage_state.json"` and returns structured session health details.

    Returns:
    {
        "has_session_file": bool,
        "has_auth_token": bool,
        "has_ct0": bool,
        "is_configured": bool,
        "status": "authenticated" | "partial" | "missing" | "expired",
        "cookie_count": int,
        "updated_at": str | None,
    }
    """
    p_dir = Path(profile_dir)
    state_file = p_dir / "storage_state.json"

    if not state_file.exists():
        return {
            "has_session_file": False,
            "has_auth_token": False,
            "has_ct0": False,
            "is_configured": False,
            "status": "missing",
            "cookie_count": 0,
            "updated_at": None,
        }

    try:
        mtime = state_file.stat().st_mtime
        updated_at = datetime.datetime.fromtimestamp(
            mtime, tz=datetime.timezone.utc
        ).isoformat()
    except Exception:
        updated_at = None

    try:
        content = state_file.read_text(encoding="utf-8").strip()
        if not content:
            return {
                "has_session_file": True,
                "has_auth_token": False,
                "has_ct0": False,
                "is_configured": False,
                "status": "missing",
                "cookie_count": 0,
                "updated_at": updated_at,
            }
        data = json.loads(content)
    except Exception as e:
        logger.warning(
            "Could not read or parse storage_state.json in %s: %s",
            profile_dir,
            e,
        )
        return {
            "has_session_file": True,
            "has_auth_token": False,
            "has_ct0": False,
            "is_configured": False,
            "status": "missing",
            "cookie_count": 0,
            "updated_at": updated_at,
        }

    cookies: list[dict[str, Any]] = []
    if isinstance(data, list):
        cookies = [c for c in data if isinstance(c, dict)]
    elif isinstance(data, dict):
        if "cookies" in data and isinstance(data["cookies"], list):
            cookies = [c for c in data["cookies"] if isinstance(c, dict)]
        else:
            # Handle key-value format in json
            for k, v in data.items():
                if isinstance(v, str):
                    cookies.append({"name": k, "value": v})

    cookie_count = len(cookies)
    has_auth_token = False
    has_ct0 = False
    now = time.time()
    is_expired = False

    for c in cookies:
        name = c.get("name")
        val = c.get("value")
        if not name or not val:
            continue

        expires = c.get("expires") or c.get("expirationDate")
        cookie_expired = False
        if expires is not None:
            try:
                exp_float = float(expires)
                if 0 < exp_float < now:
                    cookie_expired = True
            except (ValueError, TypeError):
                pass

        if name == "auth_token":
            has_auth_token = True
            if cookie_expired:
                is_expired = True

        if name == "ct0":
            has_ct0 = True
            if cookie_expired:
                is_expired = True

    if has_auth_token and has_ct0:
        if is_expired:
            status_val = "expired"
            is_configured = False
        else:
            status_val = "authenticated"
            is_configured = True
    elif has_auth_token or has_ct0 or cookie_count > 0:
        status_val = "partial"
        is_configured = False
    else:
        status_val = "missing"
        is_configured = False

    return {
        "has_session_file": True,
        "has_auth_token": has_auth_token,
        "has_ct0": has_ct0,
        "is_configured": is_configured,
        "status": status_val,
        "cookie_count": cookie_count,
        "updated_at": updated_at,
    }
