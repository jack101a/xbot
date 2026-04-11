# ─────────────────────────────────────────────────────────────
#  Stage 1: dependency builder
#  - Installs CPU-only PyTorch (no CUDA, no NVIDIA drivers)
#  - Freezes torch version so easyocr can't upgrade to CUDA wheel
#  - Pre-downloads EasyOCR Hindi + English models offline
#  Target: Intel x86_64 & Oracle ARM free tier (aarch64)
# ─────────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /install

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libglib2.0-0 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --upgrade pip && \
    # Step 1: Install CPU-only PyTorch from the PyTorch CPU wheel index.
    # This avoids the 2.5GB CUDA wheel that pip pulls from PyPI by default.
    pip install --no-cache-dir \
        torch torchvision \
        --index-url https://download.pytorch.org/whl/cpu && \
    # Step 2: Freeze the installed torch version into a constraints file.
    # This prevents pip from "upgrading" torch to the CUDA version from PyPI
    # when resolving easyocr's dependencies in the next step.
    pip freeze | grep -E "^(torch|torchvision)==" > /tmp/torch_pin.txt && \
    cat /tmp/torch_pin.txt && \
    # Step 3: Install the rest of requirements, constrained so torch stays CPU.
    pip install --no-cache-dir \
        -r requirements.txt \
        -c /tmp/torch_pin.txt \
        --extra-index-url https://download.pytorch.org/whl/cpu

# Pre-download EasyOCR models (hi + en) so runtime image is fully offline
RUN python -c "import easyocr; easyocr.Reader(['hi', 'en'], gpu=False, verbose=False)"

# ─────────────────────────────────────────────────────────────
#  Stage 2: final runtime image (lean, CPU-only, ARM-compatible)
# ─────────────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copy site-packages (CPU torch only) + CLI tools from builder
COPY --from=builder /usr/local/lib/python3.12 /usr/local/lib/python3.12
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy pre-downloaded EasyOCR model cache from builder
COPY --from=builder /root/.EasyOCR /root/.EasyOCR

# Copy backend source
COPY . /app

ENV KMP_DUPLICATE_LIB_OK=TRUE \
    OMP_NUM_THREADS=1 \
    MKL_NUM_THREADS=1 \
    # Hides all CUDA devices so PyTorch never tries to use GPU
    CUDA_VISIBLE_DEVICES="" \
    PYTHONUNBUFFERED=1 \
    EASYOCR_MODULE_PATH=/root/.EasyOCR

EXPOSE 8765

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8765/health')"

CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8765", "--workers", "1"]
