import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from question_db import question_db
from sign_db import sign_db
import uvicorn
import asyncio
import os

# ------------------------------------------------------------------ #
#  Feature Flags                                                       #
# ------------------------------------------------------------------ #
# Set AI_FALLBACK_ENABLED=true in environment (or .env) to enable
# Gemini / NVIDIA fallback. False by default for offline-first mode.
AI_FALLBACK_ENABLED = os.environ.get("AI_FALLBACK_ENABLED", "false").lower() == "true"

from contextlib import asynccontextmanager
import threading

@asynccontextmanager
async def lifespan(app):
    # Pre-warm models in a background thread so uvicorn is immediately ready
    # but models are loaded before any real question arrives (~30s on CPU).
    def _warmup():
        from ocr_engine import ocr_engine
        ocr_engine.warmup()

    t = threading.Thread(target=_warmup, daemon=True, name="model-warmup")
    t.start()
    yield
    # (shutdown — nothing to clean up)

app = FastAPI(title="MCQ Solver Pro Backend", lifespan=lifespan)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------------------------------------------------------ #
#  Request Models                                                      #
# ------------------------------------------------------------------ #
class OCRSolveRequest(BaseModel):
    image_b64: str
    dom_hints: dict = None

class LookupRequest(BaseModel):
    question_text: str

class SignLookupRequest(BaseModel):
    image_b64: str

class SolveRequest(BaseModel):
    image_b64: str
    provider: str = "gemini"

class ConfigRequest(BaseModel):
    geminiKeys: list[str] = []
    nvidiaKey: str = ""
    nvidiaModel: str = ""

# ------------------------------------------------------------------ #
#  Routes                                                              #
# ------------------------------------------------------------------ #
@app.get("/health")
def health():
    return {
        "status": "ok",
        "ai_fallback_enabled": AI_FALLBACK_ENABLED
    }

@app.post("/ocr-solve")
async def ocr_solve(request: OCRSolveRequest):
    """Primary pipeline: EasyOCR + YOLO + RapidFuzz (fully local, no API)."""
    if not request.image_b64:
        return {"found": False, "error": "Missing image"}
    from ocr_engine import ocr_engine
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None, ocr_engine.solve_screen, request.image_b64, request.dom_hints
    )
    print(f"[OCR Solve] -> {result}")
    return result

@app.post("/lookup")
async def lookup(request: LookupRequest):
    """Direct RapidFuzz question text lookup."""
    if not request.question_text:
        return {"found": False}
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, question_db.search, request.question_text)
    return result

@app.post("/sign-lookup")
async def sign_lookup(request: SignLookupRequest):
    """Legacy pHash sign lookup (kept for compatibility)."""
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, sign_db.search, request.image_b64)
    return result

@app.post("/solve")
async def solve(request: SolveRequest):
    """
    AI fallback solver (Gemini / NVIDIA).
    Currently DISABLED — returns immediately if AI_FALLBACK_ENABLED is False.
    To enable: set AI_FALLBACK_ENABLED = True and configure API keys via /config.
    """
    if not AI_FALLBACK_ENABLED:
        return {
            "answer": None,
            "disabled": True,
            "error": "AI fallback is disabled. Use /ocr-solve for local pipeline."
        }

    from solver import solve_mcq
    result = await solve_mcq(request.image_b64, request.provider)
    return result

@app.post("/config")
async def update_config(config: ConfigRequest):
    """
    Update API keys for AI providers.
    Keys are accepted but have no effect while AI_FALLBACK_ENABLED = False.
    """
    if AI_FALLBACK_ENABLED:
        from solver import key_manager, nvidia_solver
        if config.geminiKeys:
            key_manager.keys = [k for k in config.geminiKeys if k]
            key_manager._index = 0
        if config.nvidiaKey:
            os.environ["NVIDIA_API_KEY"] = config.nvidiaKey
            if config.nvidiaModel:
                os.environ["NVIDIA_MODEL"] = config.nvidiaModel
            nvidia_solver._update_client()

    return {
        "status": "config received",
        "ai_fallback_enabled": AI_FALLBACK_ENABLED
    }

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8765)
