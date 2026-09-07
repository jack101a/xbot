# Profile Authentication, Live Status & Metrics Sync Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a complete Profile Authentication, Live Session Status, and Metrics Sync subsystem that supports direct cookie paste on remote VPS, non-intrusive session health probing, live high-res avatar and follower extraction, and real-time dashboard indicators.

**Architecture:** A cookie conversion and auth inspection module (`xbot.browser.auth`) handles cookie injection and status checks, a Playwright action (`xbot.browser.actions.sync_profile_action`) scrapes live profile assets from X, FastAPI profile endpoints (`/auth-status`, `/import-cookies`, `/sync-from-x`) wire to SQLite and Analytics, and React UI components render live avatar/auth pills and the "Connect X Account" modal.

**Tech Stack:** Python 3.12+, Playwright, FastAPI, SQLAlchemy 2.0, React, Next.js / Tailwind CSS, Pytest.

**Spec:** [`docs/superpowers/specs/2026-08-18-profile-auth-and-metrics-sync-design.md`](file:///home/ubuntu/projects/xbot/docs/superpowers/specs/2026-08-18-profile-auth-and-metrics-sync-design.md)

---

### Task 1: Build Cookie Converter & Auth State Engine

**Files:**
- Create: `backend/xbot/browser/auth.py`
- Modify: `backend/xbot/browser/__init__.py`
- Test: `backend/tests/test_profile_auth.py`

**Interfaces:**
- `format_storage_state(auth_token: str, ct0: str, twid: str | None = None) -> dict`
- `parse_cookie_string(cookie_str: str) -> dict[str, str]`
- `inspect_profile_auth_status(profile_dir: Path) -> dict[str, Any]`

- [ ] **Step 1: Write unit tests in `backend/tests/test_profile_auth.py`**
- [ ] **Step 2: Run test to verify it fails** (`pytest backend/tests/test_profile_auth.py`)
- [ ] **Step 3: Implement `backend/xbot/browser/auth.py` and export cleanly**
- [ ] **Step 4: Run test to verify it passes**
- [ ] **Step 5: Commit changes (`feat(browser): add cookie converter and auth status inspector`)**

---

### Task 2: Implement `SyncProfileFromX` Playwright Browser Action

**Files:**
- Create: `backend/xbot/browser/actions/sync_profile_action.py`
- Modify: `backend/xbot/browser/actions/__init__.py` & `x_actions.py`
- Test: `backend/tests/test_sync_profile_action.py`

**Interfaces:**
- `SyncProfileFromX(BaseAction).execute(page: Page, username: str) -> dict[str, Any]`
  - Returns `{"is_authenticated": bool, "avatar_url": str, "display_name": str, "followers_count": int, "following_count": int, "bio": str, "is_verified": bool}`

- [ ] **Step 1: Write unit tests in `backend/tests/test_sync_profile_action.py`**
- [ ] **Step 2: Run test to verify it fails**
- [ ] **Step 3: Implement `backend/xbot/browser/actions/sync_profile_action.py`**
- [ ] **Step 4: Run test to verify it passes**
- [ ] **Step 5: Commit changes (`feat(browser): add SyncProfileFromX Playwright action`)**

---

### Task 3: Expose REST Endpoints for Auth Status, Cookie Import & Metrics Sync

**Files:**
- Modify: `backend/xbot/api/profiles.py`
- Test: `backend/tests/test_profile_auth_api.py`

**Interfaces:**
- `GET /api/profiles/{id}/auth-status`
- `POST /api/profiles/{id}/import-cookies`
- `POST /api/profiles/{id}/sync-from-x`

- [ ] **Step 1: Write API tests in `backend/tests/test_profile_auth_api.py`**
- [ ] **Step 2: Run test to verify it fails**
- [ ] **Step 3: Implement routes in `backend/xbot/api/profiles.py`**
- [ ] **Step 4: Run test to verify it passes**
- [ ] **Step 5: Commit changes (`feat(api): add auth-status, import-cookies, and sync-from-x endpoints`)**

---

### Task 4: Build Dashboard UI (Connect Modal, Live Avatar & Real-time Metrics)

**Files:**
- Create: `dashboard/src/components/ConnectAccountModal.tsx`
- Modify: `dashboard/src/lib/api.ts`
- Modify: `dashboard/src/app/page.tsx`

- [ ] **Step 1: Update `dashboard/src/lib/api.ts` with new API methods**
- [ ] **Step 2: Build `ConnectAccountModal.tsx` with Cookie Paste and File Upload tabs**
- [ ] **Step 3: Integrate live avatar, auth pill, and "Sync from X" button into `dashboard/src/app/page.tsx`**
- [ ] **Step 4: Build static export via `npm run build`**
- [ ] **Step 5: Commit changes (`feat(ui): add ConnectAccountModal and live profile sync badges`)**
