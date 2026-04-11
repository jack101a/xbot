document.addEventListener('DOMContentLoaded', () => {
    const powerEl = document.getElementById('power-switch');
    const debugEl = document.getElementById('debug-mode');
    const geminiKeysEl = document.getElementById('geminiKeys');
    const scoreEl = document.getElementById('stat-score');
    const safeEl = document.getElementById('stat-safe');
    const resetBtn = document.getElementById('reset-stats');
    const saveBtn = document.getElementById('save-btn');
    const solveBtn = document.getElementById('solve-btn');
    const statusEl = document.getElementById('backend-status');
    const saveConfirmEl = document.getElementById('save-confirm');

    // Load state
    chrome.storage.sync.get(['power_on', 'debug_mode', 'geminiKeys', 'provider'], (res) => {
        powerEl.checked = res.power_on !== false;
        debugEl.checked = !!res.debug_mode;
        if (res.geminiKeys) geminiKeysEl.value = res.geminiKeys.join('\n');
        if (res.provider) {
            const radio = document.querySelector(`input[name="provider"][value="${res.provider}"]`);
            if (radio) radio.checked = true;
        }
    });

    // Load stats (local storage for session persistence)
    function updateStatsUI() {
        chrome.storage.local.get(['correct', 'total'], (res) => {
            const correct = res.correct || 0;
            const total = res.total || 0;
            
            const remaining = 15 - total;
            const needed = 13 - correct;
            const safeToLose = Math.max(0, remaining - needed);

            scoreEl.textContent = correct;
            safeEl.textContent = safeToLose;
            
            if (safeToLose <= 1) {
                safeEl.style.color = "#f44336"; // Danger RED
            } else if (safeToLose <= 3) {
                safeEl.style.color = "#ffcc00"; // Caution YELLOW
            } else {
                safeEl.style.color = "#4CAF50"; // Safe GREEN
            }
        });
    }
    updateStatsUI();

    // Event Listeners
    powerEl.onchange = () => chrome.storage.sync.set({ power_on: powerEl.checked });
    debugEl.onchange = () => chrome.storage.sync.set({ debug_mode: debugEl.checked });

    resetBtn.onclick = () => {
        if(confirm("Reset exam progress?")) {
            chrome.storage.local.set({ correct: 0, total: 0 }, updateStatsUI);
        }
    };

    saveBtn.onclick = () => {
        const geminiKeys = geminiKeysEl.value.split('\n').map(k => k.trim()).filter(k => k);
        const provider = document.querySelector('input[name="provider"]:checked').value;

        chrome.storage.sync.set({ geminiKeys, provider }, () => {
            chrome.runtime.sendMessage({ 
                type: "CONFIG_UPDATE", 
                payload: { geminiKeys, debug: debugEl.checked } 
            });
            saveConfirmEl.style.display = 'inline';
            setTimeout(() => { saveConfirmEl.style.display = 'none'; }, 2000);
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
