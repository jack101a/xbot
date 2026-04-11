(function() {
    if (!window.location.hostname.includes("sarathi.parivahan.gov.in")) return;

    let isSolving = false;
    let lastQno = null;

    // --- State & Scraper ---

    async function getSettings() {
        return new Promise(resolve => {
            chrome.storage.sync.get(['power_on', 'debug_mode'], resolve);
        });
    }

    function isNewQuestion() {
        const qno = window.currqno; // native page variable
        const timer = document.getElementById("timer");
        const radio1 = document.getElementById("stallradio1");

        if (!timer || !radio1) return false;

        if (qno && qno !== lastQno) {
            lastQno = qno;
            return true;
        }
        return false;
    }

    function readQuestionText() {
        const selectors = [
            '.question-text', 'td.quesText', '#questionDiv',
            '.qtext', 'td[class*="ques"]', '.ques', '[id*="question"]'
        ];
        for (const sel of selectors) {
            const el = document.querySelector(sel);
            if (el && el.innerText.trim().length > 5) return el.innerText.trim();
        }
        return null;
    }

    function getSignImageBase64() {
        const questionSelectors = ['.question-text', 'td.quesText', '#questionDiv'];
        for (const sel of questionSelectors) {
            const el = document.querySelector(sel);
            if (!el) continue;
            const img = el.querySelector('img');
            if (img) {
                const canvas = document.createElement('canvas');
                canvas.width = img.naturalWidth || img.width;
                canvas.height = img.naturalHeight || img.height;
                const ctx = canvas.getContext('2d');
                try {
                    ctx.drawImage(img, 0, 0);
                    return canvas.toDataURL('image/png').split(',')[1];
                } catch (e) {
                    return null;
                }
            }
        }
        return null;
    }

    function getRealSecondsRemaining() {
        const el = document.getElementById("timer");
        return el ? (parseInt(el.innerHTML) || 30) : 30;
    }

    function getScoreStats() {
        const bodyText = document.body.innerText;
        const match = bodyText.match(/(?:Score|स्कोर)\s*[:\s]*(\d+)/i);
        const score = match ? parseInt(match[1]) : 0;
        const attempted = typeof window.pCount !== 'undefined' ? window.pCount : 0;
        const remaining = 15 - attempted;
        const needed = 13 - score;
        const safe = Math.max(0, remaining - needed);
        return { score, attempted, remaining, needed, safe, safeColor: safe <= 2 ? "#f44336" : (safe <= 4 ? "#ffcc00" : "#4CAF50") };
    }

    // --- DOM Hints Collector (feeds backend hybrid engine) ---

    function getRectOf(el) {
        if (!el) return null;
        const r = el.getBoundingClientRect();
        return { x: Math.round(r.left), y: Math.round(r.top), w: Math.round(r.width), h: Math.round(r.height) };
    }

    function getDomHints() {
        // Question element
        const qSelectors = ['.question-text', 'td.quesText', '#questionDiv', '.qtext', '[id*="question"]'];
        let qEl = null;
        for (const sel of qSelectors) {
            const el = document.querySelector(sel);
            if (el && el.innerText.trim().length > 5) { qEl = el; break; }
        }

        // Option elements (via radio siblings or containers)
        const options = [];
        for (let i = 1; i <= 4; i++) {
            const radio = document.getElementById(`stallradio${i}`);
            if (!radio) continue;
            const container = radio.closest('tr') || radio.closest('td') || radio.parentElement;
            const rect = getRectOf(container);
            if (rect && rect.w > 10) options.push({ num: i, rect });
        }

        const timerEl = document.getElementById("timer");
        const scoreMatch = document.body.innerText.match(/(?:Score|स्कोर)\s*[:\s]*(\d+\.?\d*)/i);

        return {
            question_no:   window.currqno || null,
            score:         scoreMatch ? parseFloat(scoreMatch[1]) : null,
            time_left:     timerEl ? (parseInt(timerEl.innerHTML) || 30) : 30,
            question_rect: getRectOf(qEl),
            options:       options.length >= 2 ? options : null   // only send if we found >= 2
        };
    }


    // --- DOM Interactions ---

    async function clickRadio(target) {
        if (!target) return false;
        let optionNumber = null;

        // If target is a number or numeric string
        if (!isNaN(target)) {
            optionNumber = parseInt(target);
        } else {
            // It's a text target! Find the radio button that matches this text.
            const targetText = target.trim().toLowerCase().replace(/\s+/g, ' ');
            let maxScore = -1;

            for (let i = 1; i <= 4; i++) {
                const radio = document.getElementById(`stallradio${i}`);
                if (!radio) continue;
                
                let container = radio.closest('tr') || radio.parentElement;
                let text = container.innerText.trim().toLowerCase().replace(/\s+/g, ' ');
                
                if (text.includes(targetText) || targetText.includes(text)) {
                    optionNumber = i; break;
                }
                
                // Fallback word overlap
                let overlap = [...new Set(text.split(' '))].filter(x => targetText.split(' ').includes(x)).length;
                if (overlap > maxScore) { maxScore = overlap; optionNumber = i; }
            }
        }

        if (!optionNumber) return false;

        const radio = document.getElementById(`stallradio${optionNumber}`);
        if (!radio) { console.error(`stallradio${optionNumber} not found`); return false; }
        if (radio.disabled) await new Promise(r => setTimeout(r, 1500));
        radio.click();
        return true;
    }

    async function submitAnswer() {
        const btn = document.getElementById("confirmbut");
        if (!btn) {
            if (document.StallExam) { document.StallExam.submit(); return; }
            return;
        }
        let waited = 0;
        while (btn.disabled && waited < 8000) {
            await new Promise(r => setTimeout(r, 300));
            waited += 300;
        }
        btn.click();
    }

    // --- UI Overlay ---

    function updateOverlay(statusText, stats = null, ocrMetadata = null) {
        let overlay = document.getElementById("mcq-solver-overlay");
        if (!overlay) {
            overlay = document.createElement("div");
            overlay.id = "mcq-solver-overlay";
            Object.assign(overlay.style, {
                position: "fixed", bottom: "15px", right: "15px", zIndex: "2147483647",
                background: "rgba(10, 10, 20, 0.95)", color: "#fff",
                fontFamily: "monospace", fontSize: "12px", padding: "12px",
                borderRadius: "8px", border: "1px solid #4facfe",
                boxShadow: "0 4px 20px rgba(0,0,0,0.5)", width: "180px", pointerEvents: "none"
            });
            document.body.appendChild(overlay);
        }

        let content = `<b>🤖 SOLVER PRO v4</b><br><hr style="border:0;border-top:1px solid #333;margin:8px 0;">`;
        content += `<span style="color:#4facfe">${statusText}</span>`;

        if (ocrMetadata) {
            content += `<br><hr style="border:0;border-top:1px solid #333;margin:8px 0;">`;
            content += `<div style="display:flex;justify-content:space-between"><span>OCR QNo:</span> <span>${ocrMetadata.qno || "0"}</span></div>`;
            content += `<div style="display:flex;justify-content:space-between"><span>OCR Score:</span> <span>${ocrMetadata.score || "0.0"}</span></div>`;
        } else if (stats) {
            content += `<br><hr style="border:0;border-top:1px solid #333;margin:8px 0;">`;
            content += `<div style="display:flex;justify-content:space-between"><span>Score:</span> <span>${stats.score}</span></div>`;
            content += `<div style="display:flex;justify-content:space-between"><span>Left:</span> <span>${stats.remaining}</span></div>`;
            content += `<div style="display:flex;justify-content:space-between;color:${stats.safeColor}"><span>Safe Fail:</span> <span><b>${stats.safe}</b></span></div>`;
        }
        
        overlay.innerHTML = content;
    }

    // --- Main Logic ---

    async function solve() {
        const settings = await getSettings();
        if (settings.power_on === false) return;
        if (isSolving) return;
        isSolving = true;

        const questionStartTime = Date.now();
        const realLeft = getRealSecondsRemaining();
        const maxAllowed = Math.min(28, realLeft - 2);
        const targetSec = (Math.random() * (maxAllowed - 11)) + 11;
        const targetFinish = questionStartTime + targetSec * 1000;

        updateOverlay("🔍 Reading question...");

        const questionText = readQuestionText();
        const signB64 = getSignImageBase64();
        const stats = getScoreStats();

        let answerOption = null;

        // PHASE 1: Local pipeline (OCR + YOLO + RapidFuzz) with DOM hints
        updateOverlay("📸 Scanning screen...");
        const domHints = getDomHints();
        const ocrResult = await chrome.runtime.sendMessage({
            type: "CAPTURE_AND_OCR",
            dom_hints: domHints
        });
        let ocrMeta = ocrResult?.metadata || null;

        if (ocrResult?.found && ocrResult.answer) {
            answerOption = ocrResult.answer;
            console.log(`[MCQ] LOCAL HIT: confidence=${ocrResult.confidence} sign=${ocrResult.sign_label} → Opt ${answerOption}`);
            updateOverlay(`✅ Local: Opt ${answerOption}`, stats, ocrMeta);
        }

        // PHASE 2: AI fallback (Gemini / NVIDIA) — disabled by default
        if (answerOption === null) {
            const { ai_fallback_enabled } = await chrome.storage.sync.get(["ai_fallback_enabled"]);
            if (ai_fallback_enabled) {
                updateOverlay("🤖 AI Fallback...", stats);
                const aiResult = await chrome.runtime.sendMessage({ type: "CAPTURE_AND_SOLVE" });
                if (aiResult?.answer && !aiResult.disabled) {
                    answerOption = aiResult.answer;
                    updateOverlay(`🤖 AI: Opt ${answerOption}`, stats);
                } else {
                    updateOverlay(`❌ AI: ${aiResult?.error || "no answer"}`, stats);
                    isSolving = false; return;
                }
            } else {
                updateOverlay("❌ No answer found", stats);
                isSolving = false; return;
            }
        }

        // PHASE 4: Wait for target time
        const waitInterval = setInterval(() => {
            const rem = Math.max(0, Math.round((targetFinish - Date.now()) / 1000));
            const pageLeft = getRealSecondsRemaining();
            let displayAns = String(answerOption);
            if (displayAns.length > 12) displayAns = displayAns.substring(0, 12) + '..';
            updateOverlay(`⏳ ${rem}s | Ans: ${displayAns}`, getScoreStats(), ocrMeta);
            if (rem === 0) clearInterval(waitInterval);
        }, 500);

        const msLeft = targetFinish - Date.now();
        if (msLeft > 0) await new Promise(r => setTimeout(r, msLeft));

        // PHASE 5: Execute answer
        await clickRadio(answerOption);
        await new Promise(r => setTimeout(r, 900));
        await submitAnswer();

        isSolving = false;
    }

    // Continuous check
    setInterval(() => {
        if (!isSolving && isNewQuestion()) {
            // Need a slight delay to allow the page rendering before reading DOM
            setTimeout(solve, 500);
        }
    }, 1500);

    // Initial check on load
    setTimeout(() => {
        if (!isSolving && getRealSecondsRemaining() > 0) {
            lastQno = window.currqno; // initialize state
            solve();
        }
    }, 2000);

})();
