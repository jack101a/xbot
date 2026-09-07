# Design Specification: Profile Authentication, Live Status & Metrics Sync

**Date:** 2026-08-18  
**Status:** APPROVED  
**Author:** Antigravity Engineering  
**System:** XBot Profile Management & Auth Subsystem  

---

## 1. Executive Summary

Provides complete visibility into account authentication status, real-time X metrics (avatar, followers, following, verification badge), and frictionless remote VPS authentication via cookie paste, storage state file upload, or interactive browser login.

---

## 2. Architecture & Data Flow

```
┌─────────────────────────────────────────────────────────────┐
│                       Dashboard UI                          │
│  - Profile Avatar (High-res `_400x400` from X)              │
│  - Status Badges: 🟢 Authenticated | 🔴 Logged Out | 🟡 2FA  │
│  - "Connect X Account" Modal (Cookie Paste / File Upload)   │
│  - "🔄 Sync from X" Instant Refresh Button                  │
└──────────────────────────────┬──────────────────────────────┘
                               │
               HTTP POST / GET │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                 FastAPI Profile API Router                  │
│  - `GET /api/profiles/{id}/auth-status`                     │
│  - `POST /api/profiles/{id}/import-cookies`                 │
│  - `POST /api/profiles/{id}/sync-from-x`                    │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                Browser Automation Engine                    │
│  - Converts `auth_token` + `ct0` -> `storage_state.json`    │
│  - Probes X DOM: `[data-testid="SideNav_AccountSwitcher"]`  │
│  - Scrapes Avatar (`pbs.twimg.com`), Followers, Following   │
│  - Saves to SQLite `Profile` & `AnalyticsSnapshot`          │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. Component Specifications

### 3.1 Backend Cookie Converter & Session Health (`xbot/browser/auth.py`)
- Standardizes cookies into Playwright `storage_state.json`:
  - `auth_token`: Domain `.x.com` / `.twitter.com`, path `/`, httpOnly `True`, secure `True`, sameSite `None` / `Lax`.
  - `ct0`: Domain `.x.com` / `.twitter.com`, path `/`, httpOnly `False`, secure `True`, sameSite `Lax`.
  - `twid`: Domain `.x.com` / `.twitter.com`, path `/`, httpOnly `False`, secure `True`.
- Helper function `format_playwright_storage_state(auth_token, ct0, twid=None) -> dict`.

### 3.2 Probe & Metrics Scraper Action (`xbot/browser/actions/sync_profile_action.py`)
- Action `SyncProfileFromX(BaseAction)`:
  - Navigates to `https://x.com/home` or `https://x.com/{handle}`.
  - Checks if logged in: `[data-testid="SideNav_AccountSwitcher_Button"]` or `[data-testid="AppTabBar_Profile_Link"]`.
  - Checks for challenge / lock screens (`/account/access`, `/login_verification`).
  - Scrapes:
    - `avatar_url`: Upgraded to `_400x400.jpg`.
    - `display_name`: From header or account switcher.
    - `followers_count`: Parsed integer.
    - `following_count`: Parsed integer.
    - `bio`: Text snippet.
    - `is_verified`: Boolean.
  - Returns structured `ProfileSyncResult`.

### 3.3 REST Endpoints (`backend/xbot/api/profiles.py`)
1. `GET /api/profiles/{id}/auth-status`:
   - Checks if `storage_state.json` exists, verifies cookie presence (`auth_token`, `ct0`), and checks expiration.
2. `POST /api/profiles/{id}/import-cookies`:
   - Accepts `{ "auth_token": "...", "ct0": "...", "raw_cookie_string": "..." }`.
   - Formats and writes `data/profiles/<slug>/storage_state.json`.
3. `POST /api/profiles/{id}/sync-from-x`:
   - Executes `SyncProfileFromX`.
   - Updates `Profile` record in DB (`avatar_url`, `followers_count`, `following_count`, `display_name`).
   - Inserts new `AnalyticsSnapshot` record.

### 3.4 Dashboard UI Components (`dashboard/src/app/page.tsx` & `dashboard/src/components/ConnectAccountModal.tsx`)
- Sidebar Profile List: Shows avatar image (with letter fallback), handle, and `🟢`/`🔴` status badge.
- Profile Header: Shows high-res avatar, live follower count, auth badge, "Connect X Account" button, and "🔄 Sync Live from X" button.
- "Connect X Account" Modal: Simple 2-tab interface (Tab 1: Fast Cookie Paste with copy guide, Tab 2: `storage_state.json` file upload).

---

## 4. Verification & Testing
- Unit tests: `test_profile_auth.py` (cookie formatting, auth-status inspection, import endpoints).
- Browser tests: `test_sync_profile_action.py` (mock X page DOM scraping for avatar, followers, login state).
- Integration test in `e2e_full_user_experience.py`.
