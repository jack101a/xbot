const BACKEND = "http://127.0.0.1:8765";

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {

    // ----------------------------------------------------------------
    //  PRIMARY: Local OCR pipeline (EasyOCR + YOLO + RapidFuzz)
    //  content.js passes dom_hints collected from the DOM
    // ----------------------------------------------------------------
    if (msg.type === "CAPTURE_AND_OCR") {
        chrome.tabs.captureVisibleTab(sender.tab.windowId, { format: "png" }, (dataUrl) => {
            if (chrome.runtime.lastError || !dataUrl) {
                sendResponse({ found: false, error: chrome.runtime.lastError?.message || "No screen data" });
                return;
            }
            const payload = {
                image_b64: dataUrl.split(",")[1],
                dom_hints: msg.dom_hints || null   // injected by content.js
            };
            fetch(`${BACKEND}/ocr-solve`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            })
            .then(r => r.json())
            .then(sendResponse)
            .catch(e => sendResponse({ found: false, error: e.message }));
        });
        return true; // async
    }

    // ----------------------------------------------------------------
    //  FALLBACK: AI solver (Gemini / NVIDIA)
    //  Disabled on the backend by default (AI_FALLBACK_ENABLED = False).
    //  This handler is kept so the extension can call it when re-enabled.
    // ----------------------------------------------------------------
    if (msg.type === "CAPTURE_AND_SOLVE") {
        chrome.storage.sync.get(["provider", "ai_fallback_enabled"], ({ provider, ai_fallback_enabled }) => {
            // Client-side guard: respect the stored flag
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
                    const resp = await fetch(`${BACKEND}/solve`, {
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
    //  Currently accepted but has no effect while AI is disabled.
    // ----------------------------------------------------------------
    if (msg.type === "CONFIG_UPDATE") {
        fetch(`${BACKEND}/config`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(msg.payload)
        }).catch(err => console.error("[BG] Config relay failed:", err));
        // Also persist ai_fallback_enabled locally
        if (msg.payload.ai_fallback_enabled !== undefined) {
            chrome.storage.sync.set({ ai_fallback_enabled: msg.payload.ai_fallback_enabled });
        }
    }

    // ----------------------------------------------------------------
    //  Direct question text lookup
    // ----------------------------------------------------------------
    if (msg.type === "QUESTION_LOOKUP") {
        fetch(`${BACKEND}/lookup`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(msg.payload)
        }).then(r => r.json()).then(sendResponse).catch(() => sendResponse({ found: false }));
        return true;
    }
});
