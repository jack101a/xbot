import json, os
from PIL import Image
import imagehash, base64, io

HAMMING_THRESHOLD = 10  # Hamming distance ≤ 10 = same sign (out of 64)

class SignDB:
    def __init__(self, db_path="data/sign_hashes.json"):
        if os.path.exists(db_path):
            self.db = json.load(open(db_path))
            print(f"[SignDB] Loaded {len(self.db)} sign hashes.")
        else:
            self.db = []
            print("[SignDB] No sign_hashes.json found. Add signs via add_sign.py.")

    def search(self, image_b64: str) -> dict:
        if not self.db:
            return {"found": False, "reason": "empty_db"}

        image_bytes = base64.b64decode(image_b64)
        img = Image.open(io.BytesIO(image_bytes))
        incoming_hash = imagehash.phash(img)

        best_match = None
        best_distance = 999

        for entry in self.db:
            stored_hash = imagehash.hex_to_hash(entry["phash"])
            distance = incoming_hash - stored_hash  # Hamming distance
            if distance < best_distance:
                best_distance = distance
                best_match = entry

        if best_distance <= HAMMING_THRESHOLD:
            return {
                "found": True,
                "answer": best_match["correct_option_number"],
                "label": best_match["label"],
                "hamming_distance": best_distance
            }
        return {"found": False, "best_distance": best_distance}

sign_db = SignDB()
