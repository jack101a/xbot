"""
Pipeline Test Script — tests each stage of the OCR solve pipeline
against real log images, saving debug images and a full report.

Usage:
    python test_pipeline.py

Output:
    test-script/output/<image_name>/
        01_original.png
        02_masked.png
        03_question_crop.png
        04_option_crops/
        05_report.txt
    test-script/output/summary.txt
"""

import sys
import os
import base64
import json
import time
import difflib

# ── path setup ──────────────────────────────────────────────────────────────
SCRIPT_DIR   = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR  = os.path.join(SCRIPT_DIR, "..", "backend")
LOG_DIR      = os.path.join(BACKEND_DIR, "logs")
OUTPUT_DIR   = os.path.join(SCRIPT_DIR, "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)
sys.path.insert(0, BACKEND_DIR)

import numpy as np
import cv2

# ── import backend modules ───────────────────────────────────────────────────
print("Loading QuestionDB...", flush=True)
os.chdir(BACKEND_DIR)
from question_db import question_db

print("Loading YOLO...", flush=True)
from ocr_engine import YOLOSignDetector
yolo = YOLOSignDetector("model/yolo.onnx")

# ── load EasyOCR once ────────────────────────────────────────────────────────
print("Loading EasyOCR (this takes ~30s first time)...", flush=True)
import easyocr
reader = easyocr.Reader(['hi', 'en'], gpu=False, verbose=False)
print("EasyOCR ready.\n", flush=True)

# ── helpers ──────────────────────────────────────────────────────────────────
def run_ocr(crop):
    if crop is None or crop.size == 0:
        return ""
    results = reader.readtext(crop, detail=0, paragraph=True)
    return " ".join(results).strip()

def mask_privacy(img):
    h, w = img.shape[:2]
    masked = img.copy()
    masked[0:int(h*0.12), 0:int(w*0.10)] = 0
    masked[0:int(h*0.12), int(w*0.10):int(w*0.55)] = 0
    return masked

def crop_question(img):
    """Visual fallback: top 10–35% of the image."""
    h = img.shape[0]
    return img[int(h*0.10):int(h*0.35), :]

def crop_options(img):
    """Visual fallback: 4 equal bands in 35–90%."""
    h, w = img.shape[:2]
    y0, y1 = int(h*0.35), int(h*0.90)
    bh = (y1 - y0) // 4
    return [(i+1, img[y0+i*bh:y0+(i+1)*bh, :]) for i in range(4)]

def save(path, img):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    cv2.imwrite(path, img)

# ── get log images (only quiz-screen images, skip login page) ────────────────
all_pngs = sorted([f for f in os.listdir(LOG_DIR) if f.endswith(".png")])
# Load each and check height — skip login/non-quiz screens (they look very different)
# We simply test all and let each stage report its findings.

print(f"Found {len(all_pngs)} images in logs.\n")

# ── run pipeline per image ───────────────────────────────────────────────────
all_results = []

for img_name in all_pngs:
    img_path = os.path.join(LOG_DIR, img_name)
    img = cv2.imread(img_path)
    if img is None:
        print(f"  [{img_name}] ❌ Could not load image")
        continue

    img_out_dir = os.path.join(OUTPUT_DIR, img_name.replace(".png", ""))
    os.makedirs(img_out_dir, exist_ok=True)

    result = {"image": img_name, "steps": {}}
    print(f"\n{'='*60}")
    print(f"  IMAGE: {img_name}  ({img.shape[1]}x{img.shape[0]})")
    print(f"{'='*60}")

    # ── STEP 1: Original ─────────────────────────────────────────────────────
    save(f"{img_out_dir}/01_original.png", img)
    print("  [1/6] ✅ Original saved")

    # ── STEP 2: Privacy Mask ─────────────────────────────────────────────────
    masked = mask_privacy(img)
    save(f"{img_out_dir}/02_masked.png", masked)
    print("  [2/6] ✅ Privacy mask applied (photo + name blacked out)")
    result["steps"]["privacy_mask"] = "applied"

    # ── STEP 3: Crop question region ─────────────────────────────────────────
    q_crop = crop_question(masked)
    save(f"{img_out_dir}/03_question_crop.png", q_crop)
    print("  [3/6] ✅ Question region cropped")

    # ── STEP 4: YOLO sign detection ──────────────────────────────────────────
    t0 = time.time()
    sign_label = yolo.predict(q_crop)
    yolo_ms = int((time.time()-t0)*1000)

    if sign_label:
        print(f"  [4/6] 🚦 YOLO detected sign: {sign_label} ({yolo_ms}ms)")
        result["steps"]["yolo"] = {"detected": sign_label, "ms": yolo_ms}
    else:
        print(f"  [4/6] ⬜ YOLO: no sign detected ({yolo_ms}ms) → text question path")
        result["steps"]["yolo"] = {"detected": None, "ms": yolo_ms}

    # ── STEP 5: QuestionDB lookup ─────────────────────────────────────────────
    db_result = None
    if sign_label:
        db_result = question_db.search_by_sign_label(sign_label)
        source = "sign_label"
    else:
        # OCR the question crop
        t0 = time.time()
        q_text = run_ocr(q_crop)
        ocr_ms = int((time.time()-t0)*1000)
        print(f"  [5a]  📝 OCR text ({ocr_ms}ms): {q_text[:80]}")
        result["steps"]["ocr_question"] = {"text": q_text, "ms": ocr_ms}

        t0 = time.time()
        db_result = question_db.search(q_text)
        rfuzz_ms = int((time.time()-t0)*1000)
        source = "text_ocr"

    if db_result and db_result.get("found"):
        print(f"  [5/6] ✅ DB match (via {source}):")
        print(f"         Correct option : {db_result['correct_option_number']}")
        print(f"         Answer text    : {db_result['correct_answer_target'][:60]}")
        print(f"         Confidence     : {db_result['confidence']}")
        result["steps"]["db_lookup"] = {
            "found": True,
            "source": source,
            "correct_option": db_result["correct_option_number"],
            "answer_text": db_result["correct_answer_target"],
            "confidence": db_result["confidence"]
        }
    else:
        print(f"  [5/6] ❌ DB: no match found")
        result["steps"]["db_lookup"] = {"found": False, "source": source}
        result["answer"] = None
        all_results.append(result)
        continue

    # ── STEP 6: Option OCR + match ────────────────────────────────────────────
    target_answer  = db_result["correct_answer_target"]
    target_opt_num = db_result["correct_option_number"]
    opt_dir = f"{img_out_dir}/04_options"
    os.makedirs(opt_dir, exist_ok=True)

    option_scores = []
    for opt_num, opt_crop in crop_options(masked):
        save(f"{opt_dir}/opt_{opt_num}.png", opt_crop)
        t0 = time.time()
        opt_text = run_ocr(opt_crop)
        sim = difflib.SequenceMatcher(None, target_answer, opt_text).ratio()
        option_scores.append((opt_num, opt_text, sim))
        print(f"         Opt {opt_num}: sim={sim:.2f}  '{opt_text[:40]}'")

    best_num, best_text, best_sim = max(option_scores, key=lambda x: x[2])

    if best_sim >= 0.35:
        final_answer = best_num
        match_method = f"visual_ocr (sim={best_sim:.2f})"
    else:
        final_answer = target_opt_num
        match_method = f"db_fallback (visual sim too low: {best_sim:.2f})"

    print(f"  [6/6] ✅ Final answer: Option {final_answer} [{match_method}]")
    result["steps"]["option_match"] = {
        "scores": [(n, round(s, 2)) for n, _, s in option_scores],
        "method": match_method
    }
    result["answer"] = final_answer

    all_results.append(result)

# ── Summary Report ────────────────────────────────────────────────────────────
print(f"\n\n{'='*60}")
print("  PIPELINE TEST SUMMARY")
print(f"{'='*60}")

yolo_hits   = sum(1 for r in all_results if r["steps"].get("yolo", {}).get("detected"))
db_hits     = sum(1 for r in all_results if r["steps"].get("db_lookup", {}).get("found"))
answered    = sum(1 for r in all_results if r.get("answer") is not None)
total       = len(all_results)

print(f"  Total images tested : {total}")
print(f"  YOLO sign detected  : {yolo_hits}/{total}")
print(f"  DB match found      : {db_hits}/{total}")
print(f"  Final answer given  : {answered}/{total}")

for r in all_results:
    status = "✅" if r.get("answer") else "❌"
    sign   = r["steps"].get("yolo", {}).get("detected") or "—"
    db_ok  = "DB✓" if r["steps"].get("db_lookup", {}).get("found") else "DB✗"
    ans    = r.get("answer", "?")
    print(f"  {status} {r['image']:35s}  sign={sign:30s}  {db_ok}  ans={ans}")

# Save JSON summary
with open(os.path.join(OUTPUT_DIR, "summary.json"), "w", encoding="utf-8") as f:
    json.dump(all_results, f, ensure_ascii=False, indent=2)
print(f"\n  Full results → test-script/output/summary.json")
print(f"  Debug images → test-script/output/<image>/")
