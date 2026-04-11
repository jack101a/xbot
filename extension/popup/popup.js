document.addEventListener('DOMContentLoaded', () => {
    const powerEl       = document.getElementById('power-switch');
    const debugEl       = document.getElementById('debug-mode');
    const geminiKeysEl  = document.getElementById('geminiKeys');
    const serverUrlEl   = document.getElementById('server-url');
    const pingStatusEl  = document.getElementById('ping-status');
    const scoreEl       = document.getElementById('stat-score');
    const safeEl        = document.getElementById('stat-safe');
    const resetBtn      = document.getElementById('reset-stats');
    const saveBtn       = document.getElementById('save-btn');
    const solveBtn      = document.getElementById('solve-btn');
    const saveConfirmEl = document.getElementById('save-confirm');

    const DEFAULT_URL = "http://127.0.0.1:8765";

    // ── Load saved settings ──────────────────────────────────────────
    chrome.storage.sync.get(
        ['power_on', 'debug_mode', 'geminiKeys', 'provider', 'server_url'],
        (res) => {
            powerEl.checked = res.power_on !== false;
            debugEl.checked = !!res.debug_mode;
            serverUrlEl.value = res.server_url || DEFAULT_URL;

            if (res.geminiKeys) geminiKeysEl.value = res.geminiKeys.join('\n');
            if (res.provider) {
                const radio = document.querySelector(`input[name="provider"][value="${res.provider}"]`);
                if (radio) radio.checked = true;
            }

            // Ping on load so user sees status immediately
            pingBackend(serverUrlEl.value);
        }
    );

    // ── Ping helper ──────────────────────────────────────────────────
    function pingBackend(url) {
        pingStatusEl.textContent = "●";
        pingStatusEl.style.color = "#888";
        chrome.runtime.sendMessage({ type: "PING_BACKEND" }, (res) => {
            if (res?.ok) {
                pingStatusEl.textContent = "● Online";
                pingStatusEl.style.color = "#4CAF50";
            } else {
                pingStatusEl.textContent = "● Offline";
                pingStatusEl.style.color = "#f44336";
            }
        });
    }

    // Re-ping when user changes the URL (with debounce)
    let pingTimer;
    serverUrlEl.addEventListener('input', () => {
        clearTimeout(pingTimer);
        pingStatusEl.textContent = "●";
        pingStatusEl.style.color = "#888";
        pingTimer = setTimeout(() => {
            // Save new URL to storage first so getBackend() uses it
            const newUrl = serverUrlEl.value.trim() || DEFAULT_URL;
            chrome.storage.sync.set({ server_url: newUrl }, () => pingBackend(newUrl));
        }, 800);
    });

    // ── Stats ────────────────────────────────────────────────────────
    function updateStatsUI() {
        chrome.storage.local.get(['correct', 'total'], (res) => {
            const correct = res.correct || 0;
            const total   = res.total   || 0;
            const remaining   = 15 - total;
            const needed      = 13 - correct;
            const safeToLose  = Math.max(0, remaining - needed);

            scoreEl.textContent = correct;
            safeEl.textContent  = safeToLose;
            safeEl.style.color  = safeToLose <= 1 ? "#f44336"
                                : safeToLose <= 3 ? "#ffcc00"
                                : "#4CAF50";
        });
    }
    updateStatsUI();

    // ── Event listeners ──────────────────────────────────────────────
    powerEl.onchange = () => chrome.storage.sync.set({ power_on: powerEl.checked });
    debugEl.onchange = () => chrome.storage.sync.set({ debug_mode: debugEl.checked });

    resetBtn.onclick = () => {
        if (confirm("Reset exam progress?")) {
            chrome.storage.local.set({ correct: 0, total: 0 }, updateStatsUI);
        }
    };

    saveBtn.onclick = () => {
        const geminiKeys = geminiKeysEl.value.split('\n').map(k => k.trim()).filter(k => k);
        const provider   = document.querySelector('input[name="provider"]:checked').value;
        const server_url = serverUrlEl.value.trim() || DEFAULT_URL;

        chrome.storage.sync.set({ geminiKeys, provider, server_url }, () => {
            chrome.runtime.sendMessage({
                type: "CONFIG_UPDATE",
                payload: { geminiKeys, debug: debugEl.checked }
            });
            saveConfirmEl.style.display = 'inline';
            setTimeout(() => { saveConfirmEl.style.display = 'none'; }, 2000);
            pingBackend(server_url);
        });
    };

    solveBtn.onclick = async () => {
        const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
        if (tab) chrome.tabs.sendMessage(tab.id, { type: "MANUAL_SOLVE" });
    };

    // Auto-refresh stats when storage changes
    chrome.storage.onChanged.addListener((changes, namespace) => {
        if (namespace === 'local' && (changes.correct || changes.total)) {
            updateStatsUI();
        }
    });
});
