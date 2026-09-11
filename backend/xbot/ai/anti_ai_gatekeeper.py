"""
Anti-AI Typography & Formatting Gatekeeper for X (Twitter).
Validates sentence casing, punctuation health, syntactic burstiness,
and rejects AI buzzword clichés, formulaic CTAs, beverage fillers, and emoji-bullet slop.
"""

from __future__ import annotations

import logging
import math
import re
import statistics
from typing import Any, NamedTuple

logger = logging.getLogger(__name__)


class ValidationResult(NamedTuple):
    is_valid: bool
    errors: list[str]
    cleaned_text: str


class AntiAIGatekeeper:
    # 1. Banned Corporate AI Clichés & Buzzwords
    BANNED_BUZZWORDS = [
        r"\bsupercharg(?:e|ed|ing|es)\b",
        r"\bunleash(?:ed|ing|es)?\b",
        r"\bharness(?:ed|ing|es)?\b",
        r"\bdelv(?:e|ed|ing|es)\b",
        r"\belevat(?:e|ed|ing|es)\b",
        r"\brevolutioniz(?:e|ed|ing|es)\b",
        r"\bstreamlin(?:e|ed|ing|es)\b",
        r"\bgame-?changer\b",
        r"\btapestry\b",
        r"\blandscape\b",
        r"\btestament\b",
        r"\bbeacon\b",
        r"\bparadigm\b",
        r"\btreasure\s+trove\b",
        r"\bcutting-?edge\b",
        r"\bseamlessly\b",
        r"\btransformative\b",
        r"\bpivotal\b",
        r"\bmultifaceted\b",
        r"\bplethora\b",
        r"\bmoreover\b",
        r"\bfurthermore\b",
        r"\bnevertheless\b",
        r"\bnotwithstanding\b",
        r"\bundoubtedly\b",
        r"\bindubitably\b",
        r"\bexemplif(?:y|ies|ying)\b",
        r"\beloquen(?:t|ce|tly)\b",
        r"\bmeticulous(?:ly)?\b",
        r"\bcommenc(?:e|ed|ing|es)\b",
        r"\butiliz(?:e|ed|ing|es)\b",
        r"\bfacilitat(?:e|ed|ing|es)\b",
        r"\bendeavou?r(?:s|ed|ing)?\b",
        r"\bsubsequently\b",
        r"\bfoster(?:s|ed|ing)?\b",
        r"\bcrucial(?:ly)?\b",
        r"\bvital(?:ly)?\b",
        r"\brobust(?:ly|ness)?\b",
        r"\bcomprehensive(?:ly)?\b",
        r"\bintricate(?:ly)?\b",
        r"\bprofound(?:ly)?\b",
        r"\bimperativ(?:e|ely)\b",
        r"\bunveils?\b",
        r"\bcurated?\b",
    ]

    # 2. Formulaic AI Openers & Closers (LinkedIn CTAs & Clichés)
    BANNED_PHRASES = [
        r"(?i)\blet\s+that\s+sink\s+in\b",
        r"(?i)\bread\s+that\s+again\b",
        r"(?i)\bagree\s+or\s+disagree\b",
        r"(?i)\bwhat\s+are\s+your\s+thoughts\??",
        r"(?i)\bdrop\s+(?:them|your\s+thoughts)\s+below\b",
        r"(?i)\bin\s+today'?s\s+(?:fast-?paced|digital|modern)\s+world\b",
        r"(?i)\blet'?s\s+dive\s+(?:in|deep|into)\b",
        r"(?i)\blook\s+no\s+further\b",
        r"(?i)\bhere'?s\s+(?:the\s+thing|why|what\s+you\s+need\s+to\s+know):?",
        r"(?i)\bit'?s\s+not\s+(?:just\s+)?about\s+.+?,\s*it'?s\s+about\b",
        r"(?i)\bnot\s+only\s+.+?,\s*but\s+also\b",
        r"(?i)\bwithout\s+further\s+ado\b",
        r"(?i)\bbuckle\s+up\b",
    ]

    # 3. Banned Routine / Beverage Filler
    BANNED_FILLER = [
        r"(?i)\bdrinking\s+chai\b",
        r"(?i)\bcup\s+of\s+chai\b",
        r"(?i)\bsipping\s+chai\b",
        r"(?i)\bcoffee\s+vs\s+matcha\b",
        r"(?i)\blukewarm\s+tea\b",
        r"(?i)\bsitting\s+on\s+terraces?\b",
        r"(?i)\bpeace\s+is\s+underrated\b",
        r"(?i)\bchai\s+rituals?\b",
        r"(?i)\bdesk\s+routine\b",
        r"(?i)\bmorning\s+routine\b",
    ]

    # 4. Emoji Bullet Pattern (Lines starting with emoji symbols)
    EMOJI_BULLET_PATTERN = re.compile(
        r"^\s*[\U00010000-\U0010ffff\u2600-\u27ff\u2b50\u2705\u2728\u274c\u27a1\U0001f300-\U0001f9ff]\s*",
        flags=re.MULTILINE,
    )

    # 5. Standard Emoji Detection Pattern
    ANY_EMOJI_PATTERN = re.compile(
        r"[\U00010000-\U0010ffff\u2600-\u27ff\u2b50\u2705\u2728\u274c\u27a1\U0001f300-\U0001f9ff]"
    )

    # 6. Sentence Splitter for Burstiness & Casing Analysis
    SENTENCE_SPLIT_REGEX = re.compile(r"(?<=[.!?])\s+|\n+")

    def validate(self, text: str, max_emojis: int = 3, persona: Any = None) -> ValidationResult:
        errors: list[str] = []
        cleaned = text.strip()

        if not cleaned:
            return ValidationResult(is_valid=False, errors=["Content is empty."], cleaned_text="")

        # -------------------------------------------------------------
        # Gatekeeper 0: Dynamic Persona Boundary Enforcement
        # -------------------------------------------------------------
        if persona and getattr(persona, "boundaries", None):
            boundaries = persona.boundaries
            # 1. Never owns check (e.g. "my gpu", "our server", "my macbook")
            for item in getattr(boundaries, "never_owns", []):
                core_item = item.split("(")[0].strip()
                if core_item:
                    keywords = [w.lower() for w in re.findall(r"\b[a-zA-Z0-9]+\b", core_item) if len(w) >= 3]
                    for kw in keywords:
                        kw_stem = kw[:-1] if kw.endswith("s") and len(kw) > 3 else kw
                        pattern = rf"\b(?:my|our)\s+(?:new\s+|custom\s+)?{re.escape(kw_stem)}s?\b"
                        if re.search(pattern, cleaned, flags=re.IGNORECASE):
                            errors.append(f"Boundary violation: Claims first-person ownership of forbidden item '{kw}' from never_owns.")

            # 2. Never claim to be check (e.g. "as a developer", "i am a software engineer")
            for role in getattr(boundaries, "never_claim_to_be", []):
                roles_split = [r.strip() for r in role.split("/") if r.strip()]
                for r_item in roles_split:
                    if len(r_item) > 2:
                        pattern = rf"\b(?:as an?|i(?:'m| am) an?)\s+{re.escape(r_item.lower())}\b"
                        if re.search(pattern, cleaned, flags=re.IGNORECASE):
                            errors.append(f"Boundary violation: Claims forbidden professional role '{r_item}' from never_claim_to_be.")

        # -------------------------------------------------------------
        # Gatekeeper 1: Banned Buzzwords & Corporate AI Clichés
        # -------------------------------------------------------------
        for pattern in self.BANNED_BUZZWORDS:
            match = re.search(pattern, cleaned, flags=re.IGNORECASE)
            if match:
                errors.append(f"Contains forbidden AI buzzword: '{match.group(0)}'.")

        for pattern in self.BANNED_PHRASES:
            match = re.search(pattern, cleaned)
            if match:
                errors.append(f"Contains formulaic AI template phrase: '{match.group(0)}'.")

        for pattern in self.BANNED_FILLER:
            match = re.search(pattern, cleaned)
            if match:
                errors.append(f"Contains banned routine/beverage filler: '{match.group(0)}'.")

        # -------------------------------------------------------------
        # Gatekeeper 2: Extreme B - Emoji Bullet Vomit & Excessive Spam
        # -------------------------------------------------------------
        emoji_matches = self.ANY_EMOJI_PATTERN.findall(cleaned)
        if len(emoji_matches) > max_emojis:
            errors.append(
                f"Too many emojis ({len(emoji_matches)} found; maximum allowed is {max_emojis}). Keep emojis natural and punchy."
            )

        if self.EMOJI_BULLET_PATTERN.search(cleaned):
            errors.append(
                "Detected emoji used as bullet list headers (e.g. 🚀, 💡, 🔥). Use standard '-' or '•' instead."
            )

        # -------------------------------------------------------------
        # Gatekeeper 3: Extreme A - Lazy WhatsApp Chat (All Lowercase / No Punctuation)
        # -------------------------------------------------------------
        paragraphs = [p.strip() for p in cleaned.split("\n\n") if p.strip()]

        # Check if text is completely lowercase (0 capital letters in entire text)
        letters = [c for c in cleaned if c.isalpha()]
        if letters:
            upper_count = sum(1 for c in letters if c.isupper())
            if upper_count == 0 and len(letters) > 20:
                errors.append("Unacceptable casing: text is entirely lowercase (lazy chat style).")
            elif (upper_count / len(letters)) > 0.60 and len(letters) > 40:
                errors.append("Unacceptable casing: text has excessive uppercase/shouting.")

        # Check that paragraph and sentence beginnings are capitalized
        for idx, para in enumerate(paragraphs, 1):
            first_char = para.lstrip("-•* 0123456789.")[:1]
            if first_char and first_char.isalpha() and not first_char.isupper():
                errors.append(
                    f"Paragraph {idx} starts with lowercase '{first_char}'. Sentences must begin with standard capitalization."
                )

        # Punctuation presence check (including bullet points and quotes)
        punct_count = sum(1 for c in cleaned if c in ".!?,:;—-\"'/()•\n")
        words = re.findall(r"\b\w+\b", cleaned)
        if len(words) > 20 and punct_count < 2:
            errors.append("Lacks standard punctuation (apostrophes, commas, periods missing).")

        # -------------------------------------------------------------
        # Gatekeeper 4: Visual Pacing & Micro-spacing (\n\n)
        # -------------------------------------------------------------
        # For long posts (>160 chars), require paragraph separation
        if len(cleaned) > 160 and "\n\n" not in cleaned and len(paragraphs) <= 1:
            errors.append("Dense wall of text: missing double line breaks (\\n\\n) for mobile readability.")

        # -------------------------------------------------------------
        # Gatekeeper 5: Syntactic Burstiness & Rhythm Variety (Prose Sentences)
        # -------------------------------------------------------------
        raw_sentences = [s.strip() for s in self.SENTENCE_SPLIT_REGEX.split(cleaned) if len(s.strip().split()) >= 3]
        # Exclude bullet list items from prose cadence check
        prose_sentences = [s for s in raw_sentences if not s.startswith(('-', '•', '*', '1.', '2.', '3.'))]
        if len(prose_sentences) >= 4:
            word_counts = [len(s.split()) for s in prose_sentences]
            try:
                stdev_length = statistics.stdev(word_counts)
                if stdev_length < 1.2:
                    errors.append(
                        f"Robotic monotone sentence rhythm (length variance std={stdev_length:.2f}). Mix short punchy sentences with longer ones."
                    )
            except Exception:
                pass

        # -------------------------------------------------------------
        # Gatekeeper 6: Repetitive Structural Parallelism
        # Detects `**Word:** Sentence` repeated 3+ times
        # -------------------------------------------------------------
        bold_list_headers = re.findall(r"^\s*[-•*]?\s*\*\*[^*]+?\*\*:", cleaned, flags=re.MULTILINE)
        if len(bold_list_headers) >= 3:
            errors.append(
                "Excessive repetitive bold headers ('**Header:** ...'). Format lists naturally without robotic headers."
            )

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            cleaned_text=cleaned,
        )

    def remediate_minor_issues(self, text: str) -> str:
        """
        Auto-corrects non-destructive typographical quirks:
        - Strips surrounding quotation marks ("...", '...', “...”).
        - Replaces smart quotes / curly apostrophes with standard clean characters.
        - Converts emoji bullets to clean standard dashes.
        - Cleans duplicate whitespace.
        """
        remediated = strip_surrounding_quotes(text)
        # Clean quotes & apostrophes
        remediated = remediated.replace("’", "'").replace("“", '"').replace("”", '"')
        # Strip outer quotes again if any remain after replacement
        remediated = strip_surrounding_quotes(remediated)
        # Replace emoji bullets at line starts with clean hyphens
        remediated = self.EMOJI_BULLET_PATTERN.sub("- ", remediated)
        # Clean double spaces
        remediated = re.sub(r"[ \t]+", " ", remediated)
        # Enforce maximum 2 hashtags
        remediated = self.enforce_max_hashtags(remediated, max_tags=2)
        return strip_surrounding_quotes(remediated.strip())

    @staticmethod
    def enforce_max_hashtags(text: str, max_tags: int = 2) -> str:
        """Strip any hashtag beyond the first `max_tags`."""
        hashtags_found = list(re.finditer(r"#\w+", text))
        if len(hashtags_found) <= max_tags:
            return text
        result = text
        for match in reversed(hashtags_found[max_tags:]):
            result = result[:match.start()] + result[match.end():]
        result = re.sub(r"  +", " ", result).strip()
        return result


def strip_surrounding_quotes(text: str) -> str:
    """
    Strips leading and trailing quotes (single, double, curly/smart quotes)
    frequently wrapped around LLM generated tweets.
    """
    cleaned = text.strip()
    quote_chars = '"\'“”‘’`'
    while len(cleaned) >= 2 and cleaned[0] in quote_chars and cleaned[-1] in quote_chars:
        cleaned = cleaned[1:-1].strip()
    return cleaned




ANTI_AI_TYPOGRAPHY_DIRECTIVE = """
=== AUTHENTIC HUMAN WRITING & DIVERSITY DIRECTIVE ===

You write with the natural variety, cadence, and spontaneity of an authentic human creator on X:

1. CADENCE, FORMATTING & STRUCTURAL FREEDOM:
   - DIVERSITY OF ARCHETYPES: Vary your post style across sessions:
     • Ultra-Short Reactions / Banter (2-15 words): e.g. "pure cinema", "real", "W", "still thinking about this", "who approved this"
     • Dry Observational Takes: Direct observations without questions or hype.
     • Sarcastic / Relatable One-Liners: Irony, self-aware wit, or contrasting before/after.
     • Nuanced Perspectives / Breakdowns: Multi-line value or trade-off breakdown with double line breaks (\n\n).
   - NEVER use "TL;DR:", "TLDR:", "In conclusion:", or "Summary:". Conclude threads and thoughts organically.

2. EMOJIS & HASHTAGS:
   - Use 0 to 2 emojis MAX (zero emojis is completely fine), chosen dynamically to fit the exact emotion and context.
   - DO NOT copy or repeat fixed emoji templates.
   - Place emojis naturally where emotional emphasis fits, never dumped formulaically at line ends.
   - STRICT LIMIT: MAXIMUM OF 2 HASHTAGS per post. Only use hashtags that directly match the specific topic entity. Zero hashtags is completely fine.
   - NEVER use emojis as bullet headers (no emojis at line starts).

3. WHITESPACE, PACING & THE 2-SENTENCE RULE:
   - Visual breathing room is MANDATORY for mobile readability and clickability.
   - THE 2-SENTENCE RULE: Never let more than two sentences run together without a double line break (\n\n).
   - Break dense paragraphs into short, digestible 1-2 sentence thoughts.
   - Vary paragraph and sentence lengths (burstiness: mix a 4-word punchline with a 15-word thought).

4. BANNED AI LEXICON & CLICHÉS (ZERO TOLERANCE):
   Do NOT use formulaic corporate/AI buzzwords, heavy essay words, or engagement-bait CTAs:
   - Buzzwords: "supercharge", "unleash", "harness", "delve", "elevate", "unlock", "revolutionize", "streamline", "game-changer", "tapestry", "landscape", "beacon", "testament", "paradigm shift", "pivotal", "plethora", "multifaceted", "bespoke"
   - Cliché openers/closers: "in today's fast-paced world", "dive in", "let's explore", "look no further", "let that sink in", "read that again", "agree or disagree?", "drop your thoughts below", "it's not just about X, it's about Y", "TL;DR", "TLDR", "In conclusion"
   - Heavy dictionary words: "moreover", "furthermore", "nevertheless", "subsequently", "utilize", "facilitate", "commence", "exemplify", "crucial", "vital", "robust", "comprehensive", "intricate", "profound", "imperative" (talk like a real person on X: "use" instead of "utilize", "start" instead of "commence", "help" instead of "facilitate").

5. BANNED ROUTINE / BEVERAGE FILLER:
   - NEVER post about drinking chai, coffee vs matcha, tea stalls, sitting on terraces, or mundane desk/morning routines.
"""
