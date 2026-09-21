# ChatGPT Bridge (Standalone v2.5.0) Integration Plan

> **Goal**: Fully integrate the standalone ChatGPT Bridge (`http://192.168.0.200:8465`) into XBot, completely replacing the heavy in-process Playwright browser from `worker-1` with lightweight, high-performance REST/OpenAI-compatible clients. Ensure the bridge URL/port is fully configurable and testable from the Next.js Dashboard.

---

## 🏗️ Architectural Overview

```
                      ┌────────────────────────────────────────┐
                      │    Standalone ChatGPT Bridge Container  │
                      │       http://192.168.0.200:8465        │
                      │  (Configurable: LAN, Port, or VPS IP)  │
                      │  - Playwright Chromium (Isolated)      │
                      │  - Real-time Quota & Session Guard     │
                      │  - DALL-E 3 / GPT-4o Image Studio      │
                      └──────────────────┬─────────────────────┘
                                         │ HTTP REST / OpenAI API
                                         │ (< 2 MB memory per request)
           ┌─────────────────────────────┼─────────────────────────────┐
           │                             │                             │
┌──────────▼────────────────────┐ ┌──────▼─────────────────────┐ ┌──────▼─────────────────────┐
│  XBot Text Generation Pipeline│ │ XBot Studio Image Generator│ │ Dashboard Settings UI      │
│  (backend/xbot/ai/client.py)  │ │ (backend/xbot/ai/chatgpt_  │ │ (dashboard/src/features/   │
│  - AsyncOpenAI(base_url="..") │ │  image.py)                 │ │  settings/ChatGPTBridgeCard│
│  - Models: chatgpt, thinking  │ │ - POST /image              │ │ - Configurable Bridge URL  │
│  - Pydantic structured output │ │ - GET /images/{filename}   │ │ - Live "Test Connection"   │
│  - < 2 MB memory per request  │ │ - Stream download to media/│ │ - Real-time Quota Badge    │
└───────────────────────────────┘ └────────────────────────────┘ └────────────────────────────┘
```

---

## 📋 Actionable Implementation Tasks

### Task 1: Configuration & Dynamic Settings (Backend)
- [ ] In `backend/xbot/config.py`:
  - Add `CHATGPT_BRIDGE_URL: str = "http://192.168.0.200:8465"`
  - Add `CHATGPT_BRIDGE_TIMEOUT: float = 180.0`
- [ ] In `backend/xbot/api/system_pkg/config_routes.py`:
  - Add `CHATGPT_BRIDGE_URL: str | None = None` to `SystemConfigUpdate`.
  - Include `CHATGPT_BRIDGE_URL` in `GET /system/config` response and persistence logic to `.env`.
  - Update `GET /system/chatgpt/status`:
    - Queries `{settings.CHATGPT_BRIDGE_URL}/status` and `{settings.CHATGPT_BRIDGE_URL}/api/accounts/quota`.
    - Returns `{ "bridge_url": ..., "online": true/false, "authenticated": true/false, "quota": {...}, "latency_ms": ... }`.
  - Update `POST /system/chatgpt/test`:
    - Accepts optional payload `{ "bridge_url": str | None }`.
    - Probes target URL `/health` and `/api/accounts/quota`.
    - Returns `{ "status": "success", "authenticated": true, "latency_ms": 45, "user": {...}, "quota": {...} }`.
- **Verification**: `curl -X POST http://localhost:8000/api/system/chatgpt/test` returns 200 with latency and quota.

---

### Task 2: Dashboard UI Configuration & Live Connection Test
- [ ] In `dashboard/src/lib/api/types.ts` & `system.ts`:
  - Add `CHATGPT_BRIDGE_URL?: string` to `SystemConfig`.
  - Update `testChatGPTLiveSession(bridgeUrl?: string)` to accept an optional URL parameter.
- [ ] In `dashboard/src/features/settings/components/ChatGPTBridgeCard.tsx`:
  - Follow `DESIGN.md` tokens (Slate surface, Indigo accents, Emerald success badges).
  - Add editable Bridge URL input (e.g. `http://192.168.0.200:8465` or custom VPS address/port).
  - Add **"Test Connection"** button (probes the entered URL immediately, showing live latency, plan type, and quota left).
  - Add **"Save Endpoint"** button (persists the new URL to system config & `.env` dynamically).
  - Display live connection indicator: `Online / Healthy` vs `Offline`.
- **Verification**: Run `npm run build` in `dashboard/` to verify zero TypeScript or JSX compile errors.

---

### Task 3: Refactor Text & Structured Completion Adapter
- [ ] In `backend/xbot/ai/chatgpt_adapter.py`:
  - Replace in-process `ChatGPT()` browser instantiation and `_bridge_lock`.
  - Implement clean `AsyncOpenAI(base_url=f"{settings.CHATGPT_BRIDGE_URL.rstrip('/')}/v1", api_key="dummy")` client.
  - Support `create()` with models `chatgpt` and `chatgpt-thinking` (with `thinking: True`).
  - Support `parse()` for structured output validation via Pydantic schema injection.
  - Implement fast failover error handling for `httpx.ConnectError` and 429 rate limits.
- [ ] In `backend/xbot/ai/client.py`:
  - Ensure provider `"chatgpt"` transparently routes through the new adapter.
- **Verification**: Run test prompt through `client.chat.completions.create(model="chatgpt/auto", messages=[...])` and verify text generation without spawning Chromium.

---

### Task 4: Refactor Studio Image Generation (REST)
- [ ] In `backend/xbot/ai/chatgpt_image.py`:
  - Replace in-process `bridge.generate_image()` with async HTTP POST to `${CHATGPT_BRIDGE_URL}/image`.
  - Payload:
    ```json
    {
      "prompt": enhanced_prompt,
      "timeout_s": timeout_s,
      "max_tries": 5,
      "client_id": "xbot"
    }
    ```
  - Parse response `image_url` (e.g. `/images/{uuid}.png`).
  - Download image via `GET ${CHATGPT_BRIDGE_URL}{image_url}` and stream-write to `target_dir` in `media/`.
  - Return local absolute path to the saved PNG.
- **Verification**: Generate an image via `generate_and_save_chatgpt_image_async("neon cyberpunk motorcycle")` and verify valid PNG exists on disk.

---

### Task 5: End-to-End Test Suite & Verification
- [ ] Run backend tests: `pytest backend/tests/test_daily_post_limit_drain.py`.
- [ ] Run frontend build: `npm --prefix dashboard run build`.
- [ ] Test dynamic URL switching: Change URL to invalid port -> test fails gracefully; restore to `http://192.168.0.200:8465` -> test succeeds.
- [ ] Run `graphify update .`.

---

## 🎯 Definition of Done
1. ChatGPT Bridge URL and port are completely configurable from the dashboard and saved to `.env`.
2. Live "Test Connection" button in the dashboard confirms connectivity, latency, and quota from the configured URL.
3. Zero Chromium processes run inside `worker-1` — worker memory stays strictly ~360 MB.
4. Both text and image generation succeed end-to-end against the remote/standalone bridge.
