import re
from typing import List, Optional, Tuple
import jellyfish
from rapidfuzz import fuzz

from app.config.settings import settings
from app.logging.logger import logger


class WakeWordDetector:
    """
    Robust Wake Word Detector utilizing phonetic and fuzzy distance matching.
    Tolerates common ASR mis-transcriptions of 'Clembot' (e.g., 'climbers', 'lambert', 'clam bot', 'clembur')
    and extracts trailing commands.
    """

    # Multi-word mis-transcriptions observed in STT logs
    MULTIWORD_VARIANTS: List[str] = [
        "fake lambert",
        "carrom board",
        "carromboard",
        "clem bird",
        "clem board",
        "claim bot",
        "clam bot",
        "klem bot",
        "climb bot",
        "clan bot",
        "clean bot",
        "clem bar",
        "clem ber",
        "clem bur",
        "clem bert",
    ]

    # Single-word mis-transcriptions
    SINGLE_WORD_VARIANTS: List[str] = [
        "clemburt",
        "clembur",
        "clembert",
        "climbers",
        "climber",
        "lambert",
        "klembot",
    ]

    MULTIWORD_REGEX = re.compile(
        r'\b(' + '|'.join(re.escape(v) for v in MULTIWORD_VARIANTS) + r')\b',
        re.IGNORECASE
    )

    def __init__(self):
        # Sort wake phrases by length descending so longer phrases match first
        self.wake_phrases = sorted([p.lower() for p in settings.wake_phrases], key=len, reverse=True)
        self.sleep_phrases = sorted([p.lower() for p in settings.sleep_phrases], key=len, reverse=True)

    @classmethod
    def is_clembot_word(cls, token: str) -> bool:
        """Checks if an individual word phonetically resembles 'clembot'."""
        t_clean = re.sub(r'[^\w]', '', token.lower()).strip()
        if not t_clean:
            return False

        if t_clean in cls.SINGLE_WORD_VARIANTS or t_clean == "clembot":
            return True

        # Restrict length to prevent accidental matches on long phrases
        if abs(len(t_clean) - len("clembot")) > 3:
            return False

        # Jaro-Winkler similarity >= 0.72
        jw = jellyfish.jaro_winkler_similarity("clembot", t_clean)
        if jw >= 0.72:
            return True

        # Sequence ratio >= 70
        ratio = fuzz.ratio("clembot", t_clean)
        if ratio >= 70:
            return True

        return False

    @classmethod
    def normalize_spoken_name(cls, text: str) -> str:
        """Replaces known and fuzzy phonetic variations of Clembot with 'clembot'."""
        # 1. Substitute multi-word regex matches first
        result = cls.MULTIWORD_REGEX.sub("clembot", text)

        # 2. Word-by-word check for single words matching clembot
        words = result.split()
        if not words:
            return result

        new_words = []
        for word in words:
            if cls.is_clembot_word(word):
                new_words.append("clembot")
            else:
                new_words.append(word)

        return " ".join(new_words)

    def check_activation(self, text: str) -> Tuple[bool, Optional[str]]:
        """
        Checks if text contains an activation phrase (e.g. 'Clembot activate yourself').
        Returns (is_activation, remaining_command_if_any).
        """
        normalized = self._normalize(text)

        # Normalize phonetic mishearings of 'activate' (e.g. 'activity yourself' -> 'activate yourself')
        normalized = re.sub(r'\bactivit(?:y|ies)\b', 'activate', normalized)

        for phrase in self.wake_phrases:
            if normalized == phrase:
                return True, None
            if normalized.startswith(phrase + " ") or normalized.startswith(phrase + ","):
                remainder = normalized[len(phrase):].strip()
                remainder = re.sub(r'^(and|please|,|\s)+', '', remainder).strip()
                return True, (remainder if remainder else None)

        # Check explicit activation pattern: 'clembot activate ...' or 'activate clembot'
        match_act = re.search(r'\bclembot\s+activate(?:\s+yourself)?\b(.*)$', normalized)
        if match_act:
            remainder = match_act.group(1).strip()
            remainder = re.sub(r'^(and|please|,|\s)+', '', remainder).strip()
            return True, (remainder if remainder else None)

        if "activate clembot" in normalized:
            remainder = normalized.split("activate clembot", 1)[1].strip()
            remainder = re.sub(r'^(and|please|,|\s)+', '', remainder).strip()
            return True, (remainder if remainder else None)

        return False, None

    def check_deactivation(self, text: str) -> bool:
        """Checks if text contains a deactivation phrase (e.g. 'Clembot deactivate')."""
        normalized = self._normalize(text)
        for phrase in self.sleep_phrases:
            if phrase in normalized:
                return True
        return False

    def strip_wake_phrase(self, text: str) -> str:
        """Strips leading wake phrases to leave just the operational command."""
        normalized = self.normalize_spoken_name(text.strip())
        lower = normalized.lower()

        # Sort wake phrases by length descending to match longest first
        for phrase in self.wake_phrases:
            if lower.startswith(phrase):
                remainder = normalized[len(phrase):].strip()
                return re.sub(r'^(and|please|,|\s)+', '', remainder, flags=re.IGNORECASE).strip()

        # Handle leading "hey clembot", "hi clembot", "ok clembot", or just "clembot"
        stripped = re.sub(r'^(?:hey|hi|ok|okay)?\s*clembot\b[\s,]*', '', normalized, flags=re.IGNORECASE).strip()
        if stripped != normalized:
            return re.sub(r'^(and|please|,|\s)+', '', stripped, flags=re.IGNORECASE).strip()

        return normalized

    @classmethod
    def _normalize(cls, text: str) -> str:
        # Normalize phonetic variations of Clembot first
        normalized = cls.normalize_spoken_name(text)
        # Strip punctuation and lower case
        cleaned = re.sub(r'[^\w\s]', '', normalized.lower())
        return " ".join(cleaned.split())
