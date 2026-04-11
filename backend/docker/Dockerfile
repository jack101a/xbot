# ─────────────────────────────────────────────────────────────
#  Stage 1: dependency builder
#  Installs all pip packages and pre-downloads EasyOCR models
#  so the final image runs fully offline.
# ─────────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /install

# System deps needed to compile opencv / easyocr
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Pre-download EasyOCR models (hi + en) into the builder layer
# so the runtime image never needs internet access.
RUN python -c "import easyocr; easyocr.Reader(['hi', 'en'], gpu=False, verbose=False)"

# ─────────────────────────────────────────────────────────────
#  Stage 2: final runtime image (lean)
# ─────────────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

WORKDIR /app

# Only the runtime system libs (no build tools)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copy pip packages from builder
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
    PYTHONUNBUFFERED=1 \
    # Disables EasyOCR from trying to re-download models
    EASYOCR_MODULE_PATH=/root/.EasyOCR

EXPOSE 8765

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8765/health')"

CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8765", "--workers", "1"]
