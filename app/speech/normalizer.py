import re
from typing import Dict, List, Optional, Tuple
import jellyfish
from rapidfuzz import fuzz

from app.logging.logger import logger


class SpeechNormalizer:
    """
    Normalizes spoken commands before parsing.
    Handles homophone variations, removes conversational filler words,
    and applies phonetic/Levenshtein matching with defined confidence thresholds.
    """

    # Common speech-to-text homophones and app name variants
    HOMOPHONE_MAP: Dict[str, str] = {
        # Databases & Tools
        "post grey sql": "postgresql",
        "postgre sql": "postgresql",
        "postgres sql": "postgresql",
        "post grace sql": "postgresql",
        "post gray sql": "postgresql",
        "postgress": "postgresql",
        "postgres": "postgresql",
        "my sequel": "mysql",
        "my sequel server": "mysql",
        "sequel server": "sql server",
        "mongo db": "mongodb",
        "maria db": "mariadb",
        "maria video": "mariadb",

        # Editors & IDEs
        "vs code": "vscode",
        "v s code": "vscode",
        "visual studio code": "vscode",
        "visual studio": "visual studio",
        "pi charm": "pycharm",
        "pie charm": "pycharm",
        "pie harm": "pycharm",
        "sublime text": "sublime",
        "sublime editor": "sublime",
        "anti gravity": "antigravity",
        "anti gravity ide": "antigravity",

        # Browsers
        "chrome browser": "chrome",
        "google chrome": "chrome",
        "edge browser": "edge",
        "ms edge": "edge",
        "microsoft edge": "edge",
        "brave browser": "brave",
        "firefox browser": "firefox",
        "mozilla firefox": "firefox",

        # System & Windows Utilities
        "file explorer": "explorer",
        "windows explorer": "explorer",
        "explorer window": "explorer",
        "my computer": "this pc",
        "task manager": "taskmgr",
        "task mgr": "taskmgr",
        "control panel": "control",
        "windows settings": "settings",
        "cmd prompt": "cmd",
        "command prompt": "cmd",
        "power shell": "powershell",
        "powershell prompt": "powershell",
        "windows terminal": "terminal",
        "recycle bin": "recycle bin",
        "trash bin": "recycle bin",

        # Web & Developer Tools
        "git hub": "github",
        "git lab": "gitlab",
        "stack overflow": "stackoverflow",
        "chat gpt": "chatgpt",
        "chat g p t": "chatgpt",
    }

    # Leading filler phrases to strip from commands
    FILLER_PREFIXES: List[str] = [
        "can you please",
        "could you please",
        "would you please",
        "please",
        "can you",
        "could you",
        "would you",
        "check carefully and",
        "check carefully",
        "tell me about",
        "tell me",
        "i want you to",
        "i need you to",
        "just",
        "kindly",
        "help me to",
        "help me",
        "do me a favor and",
        "go ahead and",
        "hey",
        "ok",
        "okay",
    ]

    CONFIDENCE_ACCEPT = 82.0
    CONFIDENCE_NEAR_MATCH = 65.0

    @classmethod
    def strip_fillers(cls, text: str) -> str:
        """Removes conversational filler prefixes from the start of a command."""
        cleaned = text.strip()
        changed = True

        while changed:
            changed = False
            lower = cleaned.lower()
            for filler in cls.FILLER_PREFIXES:
                pattern = rf'^{re.escape(filler)}\b[\s,]*'
                match = re.search(pattern, lower)
                if match:
                    cleaned = cleaned[match.end():].strip()
                    lower = cleaned.lower()
                    changed = True
                    break

        return cleaned

    @classmethod
    def replace_homophones(cls, text: str) -> str:
        """Replaces known homophone phrases with canonical terms."""
        result = text
        for homophone, canonical in cls.HOMOPHONE_MAP.items():
            pattern = rf'\b{re.escape(homophone)}\b'
            result = re.sub(pattern, canonical, result, flags=re.IGNORECASE)
        return result

    @classmethod
    def match_term(cls, query: str, candidates: List[str]) -> Tuple[Optional[str], float, str]:
        """
        Fuzzy matches query against candidate terms using RapidFuzz and Jellyfish.
        Returns (best_match_or_none, score, match_type):
          - Score >= 82: Accept match
          - Score 65 - 81: Near match ("did you mean")
          - Score < 65: Fallthrough (returns None)
        """
        if not query or not candidates:
            return None, 0.0, "none"

        q_clean = query.strip().lower()
        q_meta = jellyfish.metaphone(q_clean)

        best_cand: Optional[str] = None
        best_score = 0.0
        best_type = "none"

        for cand in candidates:
            cand_clean = cand.strip().lower()
            # 1. Exact match
            if q_clean == cand_clean:
                return cand, 100.0, "exact"

            # 2. Sequence similarity via RapidFuzz
            ratio_score = fuzz.ratio(q_clean, cand_clean)
            partial_score = fuzz.partial_ratio(q_clean, cand_clean)
            token_sort = fuzz.token_sort_ratio(q_clean, cand_clean)
            fuzz_best = max(ratio_score, partial_score * 0.9, token_sort)

            # 3. Phonetic similarity via Jellyfish
            jw_score = jellyfish.jaro_winkler_similarity(q_clean, cand_clean) * 100.0
            cand_meta = jellyfish.metaphone(cand_clean)
            meta_bonus = 15.0 if q_meta and cand_meta and (q_meta in cand_meta or cand_meta in q_meta) else 0.0

            combined_score = max(fuzz_best, jw_score + meta_bonus)
            combined_score = min(100.0, combined_score)

            if combined_score > best_score:
                best_score = combined_score
                best_cand = cand
                if combined_score >= cls.CONFIDENCE_ACCEPT:
                    best_type = "accept"
                elif combined_score >= cls.CONFIDENCE_NEAR_MATCH:
                    best_type = "near_match"
                else:
                    best_type = "none"

        if best_score >= cls.CONFIDENCE_ACCEPT:
            return best_cand, best_score, "accept"
        elif best_score >= cls.CONFIDENCE_NEAR_MATCH:
            return best_cand, best_score, "near_match"
        else:
            return None, best_score, "none"

    @classmethod
    def normalize_command(cls, raw_command: str) -> str:
        """
        End-to-end normalization of a spoken command:
        1. Strips leading filler words.
        2. Applies homophone substitutions.
        3. Collapses excess whitespace.
        """
        cleaned = cls.strip_fillers(raw_command)
        cleaned = cls.replace_homophones(cleaned)
        # Collapse multiple spaces
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        return cleaned


# Global instance
speech_normalizer = SpeechNormalizer()
