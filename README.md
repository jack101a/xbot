# MCQ Solver Pro

Offline, local-first automated MCQ solver for the Parivahan driving test portal.  
Uses **EasyOCR + YOLO ONNX + RapidFuzz** — no cloud APIs required for the primary pipeline.

---

## Stack

| Component | Technology |
|-----------|-----------|
| Backend API | FastAPI + Uvicorn |
| Sign Detection | YOLO ONNX (93 classes, 224×224) |
| Text OCR | EasyOCR (Hindi + English, CPU) |
| Question Matching | RapidFuzz `token_sort_ratio` |
| AI Fallback | Gemini / NVIDIA (disabled by default) |
| Browser Extension | Chrome/Edge MV3 |

---

## Quick Start (Docker)

```bash
# 1. Clone
git clone http://git.ajaxhs.home/ajax/mcqsolver.git
cd mcqsolver

# 2. Place your YOLO model
cp /path/to/yolo.onnx backend/model/yolo.onnx

# 3. Configure API keys (optional — AI fallback is disabled by default)
cp backend/.env.example backend/.env
# edit backend/.env if you want Gemini/NVIDIA fallback

# 4. Build & run
docker compose up --build

# Backend is live at http://localhost:8765
# Swagger docs at http://localhost:8765/docs
```

---

## Quick Start (Local / Windows)

```bat
cd backend
python -m venv venv
venv\Scripts\pip install -r requirements.txt
start.bat
```

---

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Backend status + AI flag |
| `/ocr-solve` | POST | **Primary** — full local pipeline |
| `/lookup` | POST | Direct RapidFuzz question text lookup |
| `/sign-lookup` | POST | Legacy pHash sign lookup |
| `/solve` | POST | AI fallback (disabled by default) |
| `/config` | POST | Push Gemini/NVIDIA API keys |

### `/ocr-solve` Request
```json
{
  "image_b64": "<base64 PNG>",
  "dom_hints": {
    "question_no": 5,
    "score": 2.0,
    "time_left": 27,
    "question_rect": { "x": 80, "y": 170, "w": 1200, "h": 80 },
    "options": [
      { "num": 1, "rect": { "x": 80, "y": 260, "w": 1200, "h": 60 } },
      { "num": 2, "rect": { "x": 80, "y": 340, "w": 1200, "h": 60 } },
      { "num": 3, "rect": { "x": 80, "y": 420, "w": 1200, "h": 60 } },
      { "num": 4, "rect": { "x": 80, "y": 500, "w": 1200, "h": 60 } }
    ]
  }
}
```

### Response
```json
{
  "found": true,
  "answer": 3,
  "confidence": 0.94,
  "sign_label": null,
  "answer_text": "वाहन की नम्बर प्लेट को देखकर",
  "metadata": { "qno": "5", "score": "2.0", "time": "27", "source": "dom" }
}
```

---

## Enable AI Fallback

1. `backend/main.py` → set `AI_FALLBACK_ENABLED = True`
2. Rebuild container OR restart local server
3. Extension popup → set Gemini keys via `CONFIG_UPDATE`

---

## Project Structure

```
mcqsolver/
├── backend/
│   ├── main.py              ← FastAPI server
│   ├── ocr_engine.py        ← Core pipeline (YOLO + EasyOCR + match)
│   ├── question_db.py       ← RapidFuzz question lookup
│   ├── sign_db.py           ← Legacy pHash sign lookup
│   ├── solver.py            ← Gemini/NVIDIA AI (disabled)
│   ├── dataset/
│   │   ├── questions.json   ← 300 Hindi MCQ questions
│   │   └── sign_label.json  ← Sign label → Hindi/English mapping
│   ├── model/
│   │   └── yolo.onnx        ← Sign classifier (gitignored, mount via Docker)
│   ├── Dockerfile
│   ├── requirements.txt
│   └── .env
├── extension/
│   ├── background.js        ← Screenshot capture + backend relay
│   ├── content.js           ← DOM hints + answer click
│   └── manifest.json
├── sign/                    ← Reference sign images (JPEG)
├── test-script/             ← Pipeline test scripts
├── docker-compose.yml
└── README.md
```
