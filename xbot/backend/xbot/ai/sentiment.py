from __future__ import annotations

import re
import logging
from typing import Literal

logger = logging.getLogger(__name__)

# Basic rule-based sentiment lexicon (VADER-like fallback)
POSITIVE_WORDS = {
    "love", "loved", "loves", "loving", "great", "greatest", "good", "goods", "best", "cool",
    "awesome", "amazing", "wonderful", "excellent", "beautiful", "sweet", "nice", "friendly",
    "happy", "glad", "proud", "congrats", "congratulations", "thanks", "thank", "helpful",
    "brilliant", "smart", "clever", "perfect", "genius", "agree", "correct", "spot on"
}

NEGATIVE_WORDS = {
    "hate", "hated", "hating", "hates", "bad", "worst", "worse", "stupid", "idiot", "dumb",
    "fool", "fools", "silly", "useless", "terrible", "awful", "horrible", "crap", "garbage",
    "trash", "junk", "annoying", "annoyed", "angry", "sad", "disappointed", "disappointing",
    "fail", "failed", "failure", "wrong", "incorrect", "disagree", "fake", "liar", "scam"
}

def analyze_sentiment_rules(text: str) -> Literal["positive", "neutral", "negative"]:
    """
    Performs offline, fast rule-based sentiment classification on input text.
    """
    clean_text = re.sub(r"[^\w\s]", "", text.lower())
    words = clean_text.split()
    
    pos_score = sum(1 for w in words if w in POSITIVE_WORDS)
    neg_score = sum(1 for w in words if w in NEGATIVE_WORDS)
    
    if pos_score > neg_score:
        return "positive"
    elif neg_score > pos_score:
        return "negative"
    return "neutral"


async def analyze_sentiment_llm(text: str) -> Literal["positive", "neutral", "negative"]:
    """
    Performs sentiment analysis using the fast LiteLLM model.
    """
    from xbot.ai.client import get_ai_client
    
    client = get_ai_client()
    system_prompt = (
        "You are an expert sentiment classifier. Classify the sentiment of the provided text "
        "exactly into one of: 'positive', 'neutral', or 'negative'. "
        "Return ONLY the classified word in lowercase."
    )
    try:
        response = await client.create_completion(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Text: \"{text}\""}
            ],
            temperature=0.0,
            max_tokens=10
        )
        sentiment = response.strip().lower()
        if sentiment in ["positive", "neutral", "negative"]:
            return sentiment  # type: ignore
    except Exception as e:
        logger.error("LLM sentiment analysis failed: %s. Falling back to rules.", e)
        
    return analyze_sentiment_rules(text)
