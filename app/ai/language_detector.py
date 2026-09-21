import re
from typing import Set


class LanguageDetector:
    """
    Detects non-English or Hindi/Hinglish phrasing and conversational question intents.
    Enables Clembot to route conversational or vernacular speech directly to LLM
    reasoning rather than attempting rigid English desktop automation matching.
    """

    # Common Hinglish / Romanized Hindi tokens frequently heard in Indian English ASR
    HINGLISH_TOKENS: Set[str] = {
        "kya", "hai", "ho", "kaise", "batao", "karo", "karna", "bolate", "bolte",
        "samjhe", "namaste", "dhanyawad", "shukriya", "accha", "acha", "theek",
        "kaun", "kahan", "kitna", "kitni", "kyun", "kyu", "aankh", "mein", "mera",
        "meri", "apna", "apne", "hum", "tum", "aap", "bolo", "sun", "suno", "chalo",
        "bataiye", "kripya", "madad", "haal", "kaise ho", "kya haal"
    }

    QUESTION_PATTERNS = re.compile(
        r'^(?:what|who|where|when|why|how|which|tell(?:\s+me)?|can\s+you\s+explain|explain|distance\s+between|distance\s+from|is\s+there|are\s+there|define|meaning\s+of)\b',
        re.IGNORECASE
    )

    @classmethod
    def is_devanagari(cls, text: str) -> bool:
        """Checks if text contains Devanagari script characters."""
        return bool(re.search(r'[\u0900-\u097F]', text))

    @classmethod
    def is_hinglish(cls, text: str) -> bool:
        """Checks if text contains characteristic Romanized Hindi / Hinglish tokens."""
        if cls.is_devanagari(text):
            return True

        words = re.findall(r'\b[a-zA-Z]+\b', text.lower())
        if not words:
            return False

        # Count Hinglish token matches
        matches = sum(1 for w in words if w in cls.HINGLISH_TOKENS)

        # Single characteristic strong markers
        strong_markers = {"bolate", "bolte", "kaise", "batao", "namaste", "shukriya", "kya"}
        if any(w in strong_markers for w in words):
            return True

        # Ratio of Hinglish words
        return matches >= 2 or (len(words) <= 3 and matches >= 1)

    @classmethod
    def is_conversational_question(cls, text: str) -> bool:
        """Checks if the query is an informational or conversational question."""
        cleaned = text.strip()
        if cls.QUESTION_PATTERNS.search(cleaned):
            return True
        if cleaned.endswith("?"):
            return True
        return False


language_detector = LanguageDetector()
