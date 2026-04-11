import json
import re
from rapidfuzz import process, fuzz

class QuestionDB:
    """
    Lightweight question lookup using RapidFuzz.
    No model loading, no numpy vectors — just fast fuzzy string match.
    Replaces VectorDB entirely.
    """
    THRESHOLD = 72  # Minimum similarity score (0-100)

    def __init__(self, questions_path="dataset/questions.json"):
        try:
            with open(questions_path, "r", encoding="utf-8") as f:
                self.questions = json.load(f)

            # Pre-build a flat list of (question_text, index) for fast lookup
            self.question_texts = [q["question_text"] for q in self.questions]
            print(f"[QuestionDB] Loaded {len(self.questions)} questions.")
        except FileNotFoundError:
            print(f"[QuestionDB] WARNING: {questions_path} not found.")
            self.questions = []
            self.question_texts = []

    def _normalize(self, text: str) -> str:
        """Strip punctuation and extra spaces for better fuzzy matching."""
        text = re.sub(r'[।,।\.!\?]', '', text)
        return " ".join(text.split())

    def search(self, query_text: str) -> dict:
        if not self.question_texts:
            return {"found": False, "reason": "empty_db"}

        query = self._normalize(query_text)

        # Use token_sort_ratio — best for OCR noise (word order doesn't matter)
        match = process.extractOne(
            query,
            [self._normalize(q) for q in self.question_texts],
            scorer=fuzz.token_sort_ratio
        )

        if not match:
            return {"found": False}

        matched_text, score, idx = match

        if score < self.THRESHOLD:
            return {"found": False, "best_score": score, "best_match": matched_text}

        q = self.questions[idx]
        return {
            "found":                 True,
            "confidence":            round(score / 100, 3),
            "correct_option_number": q["correct_option_number"],
            "correct_answer_target": q["correct_answer_target"],
            "question_sign_label":   q.get("question_sign_label"),
            "has_sign":              q.get("question_sign_label") is not None,
            "chapter":               q.get("chapter", ""),
            "matched_question":      q["question_text"]
        }

    def search_by_sign_label(self, sign_label: str) -> dict:
        """Direct lookup by YOLO-detected sign label."""
        matches = [q for q in self.questions if q.get("question_sign_label") == sign_label]
        if not matches:
            return {"found": False}
        # Return first match (sign questions are unique per label)
        q = matches[0]
        return {
            "found":                 True,
            "confidence":            1.0,
            "correct_option_number": q["correct_option_number"],
            "correct_answer_target": q["correct_answer_target"],
            "question_sign_label":   q["question_sign_label"],
            "has_sign":              True,
            "chapter":               q.get("chapter", ""),
            "matched_question":      q["question_text"]
        }


question_db = QuestionDB()
