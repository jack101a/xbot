# ─────────────────────────────────────────────────────────────
#  Stage 1: dependency builder
#  - Forces CPU-only PyTorch (no CUDA, no NVIDIA drivers needed)
#  - Pre-downloads EasyOCR Hindi + English models
#  - Result: runs on Intel x86 or Oracle ARM free tier
# ─────────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /install

# Minimal system libs needed to compile opencv-python-headless
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libglib2.0-0 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --upgrade pip && \
    # Install CPU-only PyTorch FIRST (before easyocr pulls the CUDA wheel)
    # This keeps the image ~500MB instead of ~2.5GB
    pip install --no-cache-dir \
        torch torchvision --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir -r requirements.txt

# Pre-download EasyOCR models (hi + en) so runtime image is fully offline
RUN python -c "import easyocr; easyocr.Reader(['hi', 'en'], gpu=False, verbose=False)"

# ─────────────────────────────────────────────────────────────
#  Stage 2: final runtime image (lean, CPU-only, ARM-compatible)
# ─────────────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

WORKDIR /app

# Only the runtime system libs (no compilers)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copy pip packages + CPU PyTorch from builder
COPY --from=builder /usr/local/lib/python3.12 /usr/local/lib/python3.12
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy pre-downloaded EasyOCR model cache from builder
COPY --from=builder /root/.EasyOCR /root/.EasyOCR

# Copy backend source
COPY . /app

# ── env vars ──────────────────────────────────────────────────
ENV KMP_DUPLICATE_LIB_OK=TRUE \
    OMP_NUM_THREADS=1 \
    MKL_NUM_THREADS=1 \
    # Prevent PyTorch from looking for CUDA
    CUDA_VISIBLE_DEVICES="" \
    PYTHONUNBUFFERED=1 \
    # Tell EasyOCR where models are (no re-download)
    EASYOCR_MODULE_PATH=/root/.EasyOCR

EXPOSE 8765

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8765/health')"

CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8765", "--workers", "1"]
