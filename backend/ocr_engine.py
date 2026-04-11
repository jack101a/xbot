import base64
import numpy as np
import cv2
import difflib
import logging
import os
import easyocr
import onnxruntime as ort

from question_db import question_db

logging.basicConfig(level=logging.WARNING)

# ------------------------------------------------------------------ #
#  YOLO ONNX Sign Detector                                            #
# ------------------------------------------------------------------ #
class YOLOSignDetector:
    """Sign classifier: input [1,3,224,224] → output [1,93] softmax probs."""
    INPUT_SIZE = 224
    CONFIDENCE_THRESHOLD = 0.55

    def __init__(self, model_path="model/yolo.onnx"):
        if not os.path.exists(model_path):
            print(f"[YOLO] WARNING: {model_path} not found. Sign detection disabled.")
            self.session = None
            return
        self.session = ort.InferenceSession(
            model_path,
            providers=["CPUExecutionProvider"]
        )
        import ast
        meta = self.session.get_modelmeta().custom_metadata_map
        self.class_names = ast.literal_eval(meta.get("names", "{}"))  # {0: 'sign_stop', ...}
        self.input_name = self.session.get_inputs()[0].name
        print(f"[YOLO] Loaded classifier: {len(self.class_names)} sign classes.")

    def predict(self, img_crop) -> str | None:
        """Return label name if confidence >= threshold, else None."""
        if self.session is None or img_crop is None or img_crop.size == 0:
            return None
        try:
            blob = cv2.resize(img_crop, (self.INPUT_SIZE, self.INPUT_SIZE))
            blob = blob[:, :, ::-1].astype(np.float32) / 255.0  # BGR->RGB, normalize
            blob = blob.transpose(2, 0, 1)[np.newaxis]           # HWC->NCHW

            probs = self.session.run(None, {self.input_name: blob})[0][0]  # shape (93,)
            best_idx = int(np.argmax(probs))
            confidence = float(probs[best_idx])

            if confidence < self.CONFIDENCE_THRESHOLD:
                print(f"[YOLO] Low confidence ({confidence:.2f}) — skipping sign path")
                return None

            label = self.class_names.get(best_idx)
            print(f"[YOLO] Detected: {label} (conf={confidence:.2f})")
            return label
        except Exception as e:
            print(f"[YOLO] Error: {e}")
            return None


# ------------------------------------------------------------------ #
#  Main OCR Engine                                                     #
# ------------------------------------------------------------------ #
class OCREngine:
    def __init__(self):
        self._ocr = None           # EasyOCR reader (lazy init)
        self._yolo = None          # YOLO detector (lazy init)

    # ---- Lazy inits ---- #
    def _get_ocr(self):
        if self._ocr is None:
            print("[OCR] Initializing EasyOCR (hi + en)...", flush=True)
            self._ocr = easyocr.Reader(['hi', 'en'], gpu=False)
        return self._ocr

    def _get_yolo(self):
        if self._yolo is None:
            self._yolo = YOLOSignDetector("model/yolo.onnx")
        return self._yolo

    # ---------------------------------------------------------------- #
    #  STEP 1 — Privacy Mask                                            #
    # ---------------------------------------------------------------- #
    def _mask_privacy(self, img):
        h, w = img.shape[:2]
        img[0:int(h*0.12), 0:int(w*0.10)] = 0        # photo
        img[0:int(h*0.12), int(w*0.10):int(w*0.55)] = 0  # name/app no
        return img

    # ---------------------------------------------------------------- #
    #  STEP 2 — Metadata (DOM first, OCR fallback on header strip)      #
    # ---------------------------------------------------------------- #
    def _extract_metadata(self, img, dom_hints):
        if dom_hints and "question_no" in dom_hints:
            return {
                "score":  str(dom_hints.get("score", "0")),
                "qno":    str(dom_hints.get("question_no", "0")),
                "time":   str(dom_hints.get("time_left", "0")),
                "source": "dom"
            }
        # Fallback: OCR the top header strip
        h = img.shape[0]
        header = img[0:int(h*0.15), :]
        texts = self._run_ocr(header)
        return {"score": "?", "qno": "?", "time": "?", "source": "ocr_header", "raw": texts}

    # ---------------------------------------------------------------- #
    #  STEP 3 — Crop question region                                    #
    # ---------------------------------------------------------------- #
    def _crop_question(self, img, dom_hints):
        if dom_hints and "question_rect" in dom_hints:
            r = dom_hints["question_rect"]
            return img[r["y"]:r["y"]+r["h"], r["x"]:r["x"]+r["w"]]
        h, w = img.shape[:2]
        return img[int(h*0.10):int(h*0.35), :]

    # ---------------------------------------------------------------- #
    #  STEP 4 — Crop each option region                                 #
    # ---------------------------------------------------------------- #
    def _crop_options(self, img, dom_hints):
        h, w = img.shape[:2]
        if dom_hints and "options" in dom_hints and len(dom_hints["options"]) >= 2:
            return [
                (o["num"], img[o["rect"]["y"]:o["rect"]["y"]+o["rect"]["h"],
                               o["rect"]["x"]:o["rect"]["x"]+o["rect"]["w"]])
                for o in dom_hints["options"]
            ]
        # Visual fallback: 4 equal bands in 35-90%
        y0, y1 = int(h*0.35), int(h*0.90)
        bh = (y1 - y0) // 4
        return [(i+1, img[y0+i*bh:y0+(i+1)*bh, :]) for i in range(4)]

    # ---------------------------------------------------------------- #
    #  STEP 5 — EasyOCR helper                                          #
    # ---------------------------------------------------------------- #
    def _run_ocr(self, crop) -> str:
        reader = self._get_ocr()
        results = reader.readtext(crop, detail=0, paragraph=True)
        return " ".join(results).strip()

    # ---------------------------------------------------------------- #
    #  STEP 6 — Detect sign in question crop via YOLO                   #
    # ---------------------------------------------------------------- #
    def _detect_sign(self, q_crop) -> str | None:
        return self._get_yolo().predict(q_crop)

    # ---------------------------------------------------------------- #
    #  PUBLIC entry point                                                #
    # ---------------------------------------------------------------- #
    def solve_screen(self, b64_str: str, dom_hints: dict = None) -> dict:
        # Decode image
        if ',' in b64_str:
            b64_str = b64_str.split(',')[1]
        try:
            img = cv2.imdecode(np.frombuffer(base64.b64decode(b64_str), np.uint8), cv2.IMREAD_COLOR)
        except Exception as e:
            return {"found": False, "error": f"Decode error: {e}"}

        if img is None:
            return {"found": False, "error": "Invalid image"}

        # 1. Privacy mask
        img = self._mask_privacy(img)

        # 2. Metadata
        metadata = self._extract_metadata(img, dom_hints)

        # 3. Crop question region
        q_crop = self._crop_question(img, dom_hints)

        # 4. Try YOLO sign detection first (fast path)
        sign_label = self._detect_sign(q_crop)

        if sign_label:
            db_result = question_db.search_by_sign_label(sign_label)
            print(f"[Engine] YOLO → {sign_label} → DB: {db_result}")
        else:
            # 4b. Text question — OCR + RapidFuzz
            question_text = self._run_ocr(q_crop)
            if not question_text:
                return {"found": False, "error": "No question text detected", "metadata": metadata}
            db_result = question_db.search(question_text)
            print(f"[Engine] OCR Q: '{question_text[:40]}' → DB: {db_result}")

        if not db_result.get("found"):
            return {
                "found": False,
                "error": "Question not in dataset",
                "metadata": metadata,
                "sign_label": sign_label
            }

        target_answer  = db_result["correct_answer_target"]
        target_opt_num = db_result["correct_option_number"]

        # 5. OCR options + fuzzy match
        option_crops = self._crop_options(img, dom_hints)
        best_option, best_score = None, 0.0

        for opt_num, opt_crop in option_crops:
            opt_text = self._run_ocr(opt_crop)
            sim = difflib.SequenceMatcher(None, target_answer, opt_text).ratio()
            print(f"  Opt {opt_num}: '{opt_text[:30]}' sim={sim:.2f}")
            if sim > best_score:
                best_score, best_option = sim, opt_num

        # If visual match is weak, trust DB option number directly
        if best_score < 0.35:
            best_option = target_opt_num
            print(f"[Engine] Weak visual match, using DB option: {target_opt_num}")

        return {
            "found":        True,
            "answer":       best_option,
            "confidence":   db_result["confidence"],
            "metadata":     metadata,
            "sign_label":   sign_label,
            "answer_text":  target_answer
        }


ocr_engine = OCREngine()
