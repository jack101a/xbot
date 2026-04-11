const DEFAULT_BACKEND = "http://127.0.0.1:8765";

/** Always reads the latest server URL from storage. */
async function getBackend() {
    return new Promise(resolve => {
        chrome.storage.sync.get({ server_url: DEFAULT_BACKEND }, ({ server_url }) => {
            resolve(server_url.replace(/\/$/, "")); // strip trailing slash
        });
    });
}

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {

    // ----------------------------------------------------------------
    //  PRIMARY: Local OCR pipeline (EasyOCR + YOLO + RapidFuzz)
    //  content.js passes dom_hints collected from the DOM
    // ----------------------------------------------------------------
    if (msg.type === "CAPTURE_AND_OCR") {
        chrome.tabs.captureVisibleTab(sender.tab.windowId, { format: "png" }, async (dataUrl) => {
            if (chrome.runtime.lastError || !dataUrl) {
                sendResponse({ found: false, error: chrome.runtime.lastError?.message || "No screen data" });
                return;
            }
            try {
                const backend = await getBackend();
                const payload = {
                    image_b64: dataUrl.split(",")[1],
                    dom_hints: msg.dom_hints || null
                };
                const resp = await fetch(`${backend}/ocr-solve`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(payload)
                });
                sendResponse(await resp.json());
            } catch (e) {
                sendResponse({ found: false, error: e.message });
            }
        });
        return true; // async
    }

    // ----------------------------------------------------------------
    //  FALLBACK: AI solver (Gemini / NVIDIA)
    //  Disabled on the backend by default (AI_FALLBACK_ENABLED = False).
    // ----------------------------------------------------------------
    if (msg.type === "CAPTURE_AND_SOLVE") {
        chrome.storage.sync.get(["provider", "ai_fallback_enabled"], ({ provider, ai_fallback_enabled }) => {
            if (!ai_fallback_enabled) {
                sendResponse({ answer: null, disabled: true, error: "AI fallback disabled" });
                return;
            }
            chrome.tabs.captureVisibleTab(sender.tab.windowId, { format: "png" }, async (dataUrl) => {
                if (chrome.runtime.lastError) {
                    sendResponse({ answer: null, error: chrome.runtime.lastError.message });
                    return;
                }
                try {
                    const backend = await getBackend();
                    const resp = await fetch(`${backend}/solve`, {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({
                            image_b64: dataUrl.split(",")[1],
                            provider: provider || "gemini"
                        })
                    });
                    sendResponse(await resp.json());
                } catch (e) {
                    sendResponse({ answer: null, error: e.message });
                }
            });
        });
        return true;
    }

    // ----------------------------------------------------------------
    //  CONFIG: Push API keys to backend
    // ----------------------------------------------------------------
    if (msg.type === "CONFIG_UPDATE") {
        getBackend().then(backend => {
            fetch(`${backend}/config`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(msg.payload)
            }).catch(err => console.error("[BG] Config relay failed:", err));
        });
        if (msg.payload.ai_fallback_enabled !== undefined) {
            chrome.storage.sync.set({ ai_fallback_enabled: msg.payload.ai_fallback_enabled });
        }
    }

    // ----------------------------------------------------------------
    //  Direct question text lookup
    // ----------------------------------------------------------------
    if (msg.type === "QUESTION_LOOKUP") {
        getBackend().then(backend => {
            fetch(`${backend}/lookup`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(msg.payload)
            }).then(r => r.json()).then(sendResponse).catch(() => sendResponse({ found: false }));
        });
        return true;
    }

    // ----------------------------------------------------------------
    //  HEALTH CHECK (called by popup to ping the configured server)
    // ----------------------------------------------------------------
    if (msg.type === "PING_BACKEND") {
        getBackend().then(backend => {
            fetch(`${backend}/health`, { signal: AbortSignal.timeout(3000) })
                .then(r => r.json())
                .then(data => sendResponse({ ok: true, url: backend, data }))
                .catch(e => sendResponse({ ok: false, url: backend, error: e.message }));
        });
        return true;
    }
});
