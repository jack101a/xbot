Here's the full architecture walkthrough:

---

## MCQ Solver Pro — How It All Works

### 🔁 Trigger
```
content.js polls every 1500ms
  └─ window.currqno changed? → wait 500ms → solve()
```

---

### 📋 Step 1 — DOM Hints (content.js)
Before screenshot, read the live page:
```js
getDomHints() → {
  question_no:   10,
  score:         8.0,
  time_left:     27,
  question_rect: { x, y, w, h },   // from getBoundingClientRect()
  options: [
    { num: 1, rect: {x,y,w,h} },   // stallradio1's container
    { num: 2, rect: {x,y,w,h} },
    { num: 3, rect: {x,y,w,h} },
    { num: 4, rect: {x,y,w,h} }
  ]
}
```

---

### 📸 Step 2 — Screenshot (background.js)
```
sendMessage({ type: "CAPTURE_AND_OCR", dom_hints })
  └─ captureVisibleTab() → PNG base64
       └─ POST /ocr-solve { image_b64, dom_hints }
```

---

### ⬛ Step 3 — Privacy Mask (ocr_engine.py)
```
Top-left 10%×12%  → BLACK  (photo)
Next 45% same row → BLACK  (name + app number)
```

---

### 🟩 Step 4 — Metadata (Hybrid)
```
dom_hints has question_no?
  ├─ YES → use directly                    [fast, accurate]
  └─ NO  → EasyOCR on top 15% header strip [fallback]
```

---

### 🚦 Step 5 — YOLO Sign Classifier
```
Crop question region (from dom_hints.question_rect or top 10–35%)
  └─ yolo.onnx: 224×224 input → [1,93] softmax output
       ├─ confidence ≥ 0.55 → label e.g. "sign_give_way"
       └─ confidence < 0.55 → None → go to text OCR
```

---

### 🟥 Step 6 — Two Paths Based on Sign Detection

**Path A — Sign Question:**
```
sign_label "sign_give_way"
  └─ question_db.search_by_sign_label()
       └─ direct dict lookup → { answer: 1, answer_text: "रास्ता दीजिए" }
```

**Path B — Text Question:**
```
EasyOCR on question crop → raw Hindi text
  └─ question_db.search(text)   [RapidFuzz token_sort_ratio ≥ 72]
       └─ { correct_option_number, correct_answer_target }
```

---

### 🟧 Step 7 — Option Matching
```
Crop each option (dom_hints rects or 4 equal bands in 35–90%)
  └─ EasyOCR each option → text
       └─ difflib similarity vs correct_answer_target
            ├─ best match ≥ 0.35 → use that option number
            └─ all weak        → use DB's correct_option_number directly
```

---

### ⏳ Step 8 — Human-like Delay
```
Random wait: 11–28 seconds (respects time remaining)
  └─ countdown shown in overlay → submit
```

---

### ✅ Step 9 — Submit
```
stallradio{N}.click()
  └─ wait 900ms → #confirmbut.click()
```

---

### 🤖 Step 10 — AI Fallback (Disabled)
Only fires if Steps 1–9 return no answer **AND** `ai_fallback_enabled = true`
```
chrome.storage: ai_fallback_enabled?
  ├─ false → "❌ No answer found"  (current default)
  └─ true  → POST /solve → Gemini or NVIDIA → answer
```

**To enable:** flip `AI_FALLBACK_ENABLED = True` in `main.py` + set flag via popup `CONFIG_UPDATE`

---

### Complete Data Flow
```
Page → content.js (DOM hints)
     → background.js (screenshot)
     → /ocr-solve
          ├─ ⬛ Privacy mask
          ├─ 🟩 Metadata (DOM/OCR)
          ├─ 🚦 YOLO classifier
          ├─ 🟥 question_db lookup
          └─ 🟧 Option EasyOCR match
     → { answer: 3 }
     → content.js → click radio → confirm
```