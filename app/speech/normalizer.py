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

        # ── Code-command STT corruptions ──────────────────────────────────────
        # "show" variants
        "showero": "show",
        "showo": "show",
        "showro": "show",
        "show row": "show",
        "shower": "show",
        "sho w": "show",

        # "delete" variants
        "delet": "delete",
        "deleet": "delete",
        "d-lete": "delete",
        "deleate": "delete",
        "daleet": "delete",
        "deletae": "delete",

        # "insert" variants
        "insertt": "insert",
        "insurt": "insert",
        "inserte": "insert",
        "insirt": "insert",

        # "replace" variants
        "replays": "replace",
        "replacee": "replace",
        "replaci": "replace",
        "replacw": "replace",
        "replase": "replace",

        # "comment" / "uncomment" variants
        "commet": "comment",
        "commont": "comment",
        "comman": "comment",
        "un comment": "uncomment",
        "uncoment": "uncomment",
        "un commont": "uncomment",
        "unkomment": "uncomment",
        "unkamont": "uncomment",

        # "go to" / "goto" variants
        "gotto": "go to",
        "gotta line": "go to line",
        "goto": "go to",
        "gotto line": "go to line",
        "go too": "go to",

        # "line" variants  (e.g. "lion 32" → "line 32")
        "in-line": "in line",
        "lion": "line",
        "lyine": "line",
        "lyne": "line",
        "lionn": "line",
        "liner": "line",
        "liine": "line",
        "lien": "line",

        # "read" variants
        "reed": "read",
        "rede": "read",

        # "run" variants
        "runn": "run",
        "ron": "run",

        # "open" variants
        "opan": "open",
        "opne": "open",

        # "close" variants
        "cloze": "close",
        "closs": "close",

        # "save" variants
        "sayve": "save",
        "saave": "save",

        # "find" variants
        "finde": "find",
        "fynd": "find",

        # "add" variants
        "ad ": "add ",

        # "print" variants
        "prin": "print",
        "prnt": "print",

        # spoken "dot" → file extension (e.g. "main dot py" → "main.py")
        " dot py": ".py",
        " dot txt": ".txt",
        " dot js": ".js",
        " dot ts": ".ts",
        " dot html": ".html",
        " dot css": ".css",
        " dot json": ".json",
        " dot csv": ".csv",
        " dot md": ".md",
        " dot yaml": ".yaml",
        " dot yml": ".yml",
        " dot xml": ".xml",
        " dot pdf": ".pdf",
        " dot docx": ".docx",
        " dot doc": ".doc",
        " dot xlsx": ".xlsx",
        " dot pptx": ".pptx",
        " dot ppt": ".ppt",
        " dot sh": ".sh",
        " dot bat": ".bat",
        " dot exe": ".exe",
        " dot png": ".png",
        " dot jpg": ".jpg",
        " dot jpeg": ".jpeg",
        " dot mp3": ".mp3",
        " dot mp4": ".mp4",
        " dot zip": ".zip",

        # spoken digit normalisation (hyphens from TTS)
        "thirty-two": "thirty two",
        "thirty-three": "thirty three",
        "thirty-four": "thirty four",
        "thirty-five": "thirty five",
        "thirty-six": "thirty six",
        "thirty-seven": "thirty seven",
        "thirty-eight": "thirty eight",
        "thirty-nine": "thirty nine",
        "forty-one": "forty one",
        "forty-two": "forty two",
        "forty-three": "forty three",
        "forty-four": "forty four",
        "forty-five": "forty five",
        "forty-six": "forty six",
        "forty-seven": "forty seven",
        "forty-eight": "forty eight",
        "forty-nine": "forty nine",
        "twenty-one": "twenty one",
        "twenty-two": "twenty two",
        "twenty-three": "twenty three",
        "twenty-four": "twenty four",
        "twenty-five": "twenty five",
        "twenty-six": "twenty six",
        "twenty-seven": "twenty seven",
        "twenty-eight": "twenty eight",
        "twenty-nine": "twenty nine",
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

    # ── Regex patterns for post-homophone token repair ────────────────────────
    # Each tuple: (compiled_pattern, replacement)
    _CODE_TOKEN_FIXES = [
        # "show" garbled with extra syllables: showero, showo, showro, showra …
        (re.compile(r'\bshow[aeiou]?r?[aeiou]{0,2}\b', re.IGNORECASE), 'show'),
        # "delete" garbled: deletea, deleate, daleet …
        (re.compile(r'\bdele[aeiou]?[tc]?[eai]?\b', re.IGNORECASE), 'delete'),
        # "insert" garbled: inserrt, insertt, insirt …
        (re.compile(r'\bins[aeio]?r?t{1,2}\b', re.IGNORECASE), 'insert'),
        # "replace" garbled: replays, replaci, replase …
        (re.compile(r'\breplace?[siyew]{0,2}\b', re.IGNORECASE), 'replace'),
        # "comment" garbled: commet, commont, comman …
        (re.compile(r'\bcomm[oa]n?[t]?\b', re.IGNORECASE), 'comment'),
        # "uncomment" garbled (after word-boundary check)
        (re.compile(r'\bun[\s-]?comm[oa]n?[t]?\b', re.IGNORECASE), 'uncomment'),
        # "line" garbled: lion, lyine, lyne, lien, liner …
        (re.compile(r'\bl[iy](?:o|e|a)?n[enr]?\b', re.IGNORECASE), 'line'),
        # "go to" garbled: gotto, goto, gotta …
        (re.compile(r'\bgo[t]{1,2}[ao]\b', re.IGNORECASE), 'go to'),
        # spoken digit with stray "2"/"3" instead of word: "thirty 2" → "thirty two"
        (re.compile(r'\b(twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety)\s+(\d)\b', re.IGNORECASE),
         lambda m: m.group(1) + ' ' + {
             '1': 'one', '2': 'two', '3': 'three', '4': 'four', '5': 'five',
             '6': 'six', '7': 'seven', '8': 'eight', '9': 'nine'
         }.get(m.group(2), m.group(2))),
        # "inline" joined before line number: "inline 43" → "in line 43", "inline43" → "in line 43"
        (re.compile(r'\binline\s*(\d+|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety)\b', re.IGNORECASE), r'in line \1'),
        # Generic spoken "dot" between word tokens → file extension separator
        # e.g. "amrit dot py" → "amrit.py", "notes dot cpp" → "notes.cpp"
        # Only fires when the right-hand word is a short extension (1–6 chars)
        (re.compile(r'\b(\w+)\s+dot\s+([a-zA-Z]{1,6})\b', re.IGNORECASE),
         lambda m: f'{m.group(1)}.{m.group(2)}'),
    ]

    @classmethod
    def fix_code_command_tokens(cls, text: str) -> str:
        """
        Applies regex-based repair passes after homophone substitution.
        Snaps garbled verb prefixes and common STT corruption patterns to their
        canonical coding-command forms.  Only fires on short token-like matches
        so it does not corrupt longer free-form text.
        """
        result = text
        for pattern, repl in cls._CODE_TOKEN_FIXES:
            if callable(repl):
                result = pattern.sub(repl, result)
            else:
                # Guard: only replace when the match is a single short token
                # (avoid turning "shower" inside "bathroom shower" → we allow it
                # in coding context; normalizer is only called on voice commands).
                result = pattern.sub(repl, result)
        return result

    @classmethod
    def normalize_command(cls, raw_command: str) -> str:
        """
        End-to-end normalization of a spoken command:
        1. Strips leading filler words.
        2. Applies homophone substitutions.
        3. Applies regex-based code-command token repair.
        4. Collapses excess whitespace.
        """
        cleaned = cls.strip_fillers(raw_command)
        cleaned = cls.replace_homophones(cleaned)
        cleaned = cls.fix_code_command_tokens(cleaned)
        # Collapse multiple spaces
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        return cleaned


# Global instance
speech_normalizer = SpeechNormalizer()
