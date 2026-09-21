"""
app/editor/code_edit_parser.py

Parses natural-language voice commands into structured code-edit tokens that the
ActionRouter can execute directly on a file without an AI round-trip.

Token format (stored in AgentAction.text):
    REPLACE_IN_LINE:{line}:{old}::{new}   — replace first occurrence of <old> with <new> on line N
    REPLACE_ALL_IN_LINE:{line}:{old}::{new} — replace all occurrences on line N
    REPLACE_LINE:{line}::{new_text}       — overwrite entire line N
    DELETE_LINE:{line}                    — delete line N
    DELETE_LINES:{start}:{end}            — delete lines start..end (inclusive)
    INSERT_AFTER:{line}::{text}           — insert a new line after line N
    INSERT_BEFORE:{line}::{text}          — insert a new line before line N
    COMMENT_LINE:{line}                   — comment out line N (adds # / //)
    UNCOMMENT_LINE:{line}                 — remove leading comment char from line N
    RENAME_FUNC:{old}:{new}              — rename function (whole-file, already supported)
    ADD_TRY_EXCEPT:{line}                — wrap line N in try/except

The separator "::" is used between the line/params and the text payload to avoid
ambiguity when the text itself contains colons.
"""

import re
from dataclasses import dataclass
from typing import Optional, Tuple


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass
class ParsedEditCommand:
    token: str          # The full token string for AgentAction.text
    line_number: int    # Primary line number (0 if not applicable)
    summary: str        # Human-readable description for TTS reply


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

# Spoken number words → digits
_WORD_NUMS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14,
    "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18,
    "nineteen": 19, "twenty": 20, "thirty": 30, "forty": 40,
    "fifty": 50, "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90,
}


def _parse_line_number(raw: str) -> Optional[int]:
    """Convert a spoken line reference ('6', 'six', 'line 6') to an int."""
    raw = raw.strip().lower().replace("line", "").strip()
    if raw.isdigit():
        return int(raw)
    return _WORD_NUMS.get(raw)


def parse_voice_edit(command: str) -> Optional[ParsedEditCommand]:
    """
    Attempts to parse a voice edit command.
    Returns a ParsedEditCommand on success, None if the command is not
    a recognised deterministic edit (caller should fall back to AI).

    Handles all of the following patterns (examples):
        "in line 6 replace char with int"
        "on line 6 change char to int"
        "line 6 replace char keyword with int"
        "replace char with int on line 6"
        "at line 10 delete the word hello"
        "delete line 10"
        "delete lines 5 to 8"
        "remove line 10"
        "in line 4 change the whole line to x = 0"
        "replace entire line 4 with x = 0"
        "insert print hello after line 5"
        "add a new line after line 5 saying print hello"
        "insert before line 3: x = 0"
        "comment out line 7"
        "uncomment line 7"
        "rename function foo to bar"
        "add try except at line 12"
        "wrap line 12 in error handling"
    """
    cmd = command.strip()

    # ----- helpers -----
    LINE_RE = r'(?:line\s+)?(\d+|' + '|'.join(_WORD_NUMS.keys()) + r')'

    # 1. DELETE LINE(S)
    # "delete line 10", "remove line 10", "erase line 10"
    m = re.search(
        r'^(?:delete|remove|erase)\s+line\s+(\w+)[.!?]*$',
        cmd, re.IGNORECASE
    )
    if m:
        ln = _parse_line_number(m.group(1))
        if ln:
            return ParsedEditCommand(
                token=f"DELETE_LINE:{ln}",
                line_number=ln,
                summary=f"Deleting line {ln}."
            )

    # "delete lines 5 to 8 / 5 through 8 / 5 and 8"
    m = re.search(
        r'^(?:delete|remove|erase)\s+lines?\s+(\w+)\s+(?:to|through|and)\s+(\w+)[.!?]*$',
        cmd, re.IGNORECASE
    )
    if m:
        s = _parse_line_number(m.group(1))
        e = _parse_line_number(m.group(2))
        if s and e:
            return ParsedEditCommand(
                token=f"DELETE_LINES:{s}:{e}",
                line_number=s,
                summary=f"Deleting lines {s} to {e}."
            )

    # 2. REPLACE WORD/PHRASE IN LINE
    # "in line 6 replace char with int"
    # "on line 6 change char to int"
    # "at line 6 replace the char keyword with int"
    # "replace char with int on line 6 / in line 6"
    replace_patterns = [
        # <position> <verb> [the] <old> [keyword/word/text/thing] <connector> <new>
        r'^(?:in|on|at)\s+line\s+(\w+)\s+(?:replace|change|swap|update)\s+(?:the\s+)?(.+?)\s+(?:with|to)\s+(.+?)[.!?]*$',
        # replace <old> with <new> [in/on] line N
        r'^(?:replace|change|swap|update)\s+(?:the\s+)?(.+?)\s+(?:with|to)\s+(.+?)\s+(?:in|on|at)\s+line\s+(\w+)[.!?]*$',
        # in line N change X to Y (alt word order)
        r'^(?:in|on|at)\s+line\s+(\w+)\s+(?:change|set)\s+(?:the\s+)?(.+?)\s+to\s+(.+?)[.!?]*$',
    ]
    for i, pat in enumerate(replace_patterns):
        m = re.search(pat, cmd, re.IGNORECASE)
        if m:
            if i in (0, 2):
                ln_raw, old, new = m.group(1), m.group(2), m.group(3)
            else:  # pattern 1: old, new, line
                old, new, ln_raw = m.group(1), m.group(2), m.group(3)

            ln = _parse_line_number(ln_raw)
            old = _clean_spoken_qualifier(old)
            new = new.strip().rstrip('.!?')
            if ln and old and new:
                return ParsedEditCommand(
                    token=f"REPLACE_IN_LINE:{ln}:{old}::{new}",
                    line_number=ln,
                    summary=f"Replacing '{old}' with '{new}' on line {ln}."
                )

    # 3. REPLACE ENTIRE LINE
    # "replace line 4 with x = 0"
    # "replace entire line 4 with x = 0"
    # "in line 4 change the whole line to x = 0"
    m = re.search(
        r'^(?:replace|rewrite|overwrite|set)\s+(?:(?:the\s+)?entire\s+|(?:the\s+)?whole\s+)?line\s+(\w+)\s+(?:with|to)\s+(.+?)[.!?]*$',
        cmd, re.IGNORECASE
    )
    if not m:
        m = re.search(
            r'^(?:in|on|at)\s+line\s+(\w+)\s+(?:change|replace|rewrite)\s+(?:the\s+)?(?:whole|entire)\s+line\s+(?:to|with)\s+(.+?)[.!?]*$',
            cmd, re.IGNORECASE
        )
    if m:
        ln = _parse_line_number(m.group(1))
        new_text = m.group(2).strip().rstrip('.!?')
        if ln:
            return ParsedEditCommand(
                token=f"REPLACE_LINE:{ln}::{new_text}",
                line_number=ln,
                summary=f"Replacing line {ln} with: {new_text}"
            )

    # 4. INSERT AFTER LINE
    # "insert print hello after line 5"
    # "add a new line after line 5 saying / with: print hello"
    m = re.search(
        r'^(?:insert|add)\s+(?:a\s+)?(?:new\s+)?(?:line\s+)?(.+?)\s+after\s+line\s+(\w+)[.!?]*$',
        cmd, re.IGNORECASE
    )
    if not m:
        m = re.search(
            r'^(?:after\s+line\s+(\w+))\s+(?:add|insert)\s+(?:a\s+)?(?:new\s+line\s+)?(?:saying\s+|with\s+)?(.+?)[.!?]*$',
            cmd, re.IGNORECASE
        )
        if m:
            m = type('M', (), {'group': lambda self, i: [None, m.group(2), m.group(1)][i]})()

    if m:
        text = m.group(1).strip()
        ln = _parse_line_number(m.group(2))
        # Remove "saying" / "with:" from text
        text = re.sub(r'^(?:saying|with\s*:)\s*', '', text, flags=re.IGNORECASE).strip().rstrip('.!?')
        if ln and text:
            return ParsedEditCommand(
                token=f"INSERT_AFTER:{ln}::{text}",
                line_number=ln,
                summary=f"Inserting '{text}' after line {ln}."
            )

    # 5. INSERT BEFORE LINE
    # "insert x = 0 before line 3"
    # "add before line 3: x = 0"
    m = re.search(
        r'^(?:insert|add)\s+(?:a\s+)?(?:new\s+)?(?:line\s+)?(.+?)\s+before\s+line\s+(\w+)[.!?]*$',
        cmd, re.IGNORECASE
    )
    if m:
        text = m.group(1).strip().rstrip('.!?')
        ln = _parse_line_number(m.group(2))
        if ln and text:
            return ParsedEditCommand(
                token=f"INSERT_BEFORE:{ln}::{text}",
                line_number=ln,
                summary=f"Inserting '{text}' before line {ln}."
            )

    # 6. COMMENT / UNCOMMENT LINE
    m = re.search(
        r'^(?:comment\s+out|comment)\s+line\s+(\w+)[.!?]*$',
        cmd, re.IGNORECASE
    )
    if m:
        ln = _parse_line_number(m.group(1))
        if ln:
            return ParsedEditCommand(
                token=f"COMMENT_LINE:{ln}",
                line_number=ln,
                summary=f"Commenting out line {ln}."
            )

    m = re.search(
        r'^uncomment\s+line\s+(\w+)[.!?]*$',
        cmd, re.IGNORECASE
    )
    if m:
        ln = _parse_line_number(m.group(1))
        if ln:
            return ParsedEditCommand(
                token=f"UNCOMMENT_LINE:{ln}",
                line_number=ln,
                summary=f"Uncommenting line {ln}."
            )

    # 7. RENAME FUNCTION  (pass through to existing handler)
    m = re.search(
        r'^(?:rename|change)\s+(?:the\s+)?function(?:\s+name)?\s+(\w+)\s+to\s+(\w+)[.!?]*$',
        cmd, re.IGNORECASE
    )
    if m:
        return ParsedEditCommand(
            token=f"RENAME_FUNC:{m.group(1)}:{m.group(2)}",
            line_number=0,
            summary=f"Renaming function {m.group(1)} to {m.group(2)}."
        )

    # 8. ADD TRY-EXCEPT
    m = re.search(
        r'^(?:add\s+(?:a\s+)?try\s*(?:except|catch)|wrap\s+.*?in\s+(?:a\s+)?(?:try|error\s+handling)).*?(?:at\s+line\s+(\w+))?[.!?]*$',
        cmd, re.IGNORECASE
    )
    if m:
        ln = _parse_line_number(m.group(1)) if m.group(1) else 1
        return ParsedEditCommand(
            token=f"ADD_TRY_EXCEPT:{ln}",
            line_number=ln,
            summary=f"Wrapping line {ln} in a try-except block."
        )

    return None


def _clean_spoken_qualifier(text: str) -> str:
    """Strip trailing spoken qualifiers like 'keyword', 'word', 'text', 'thing', 'value'."""
    text = text.strip()
    text = re.sub(
        r'\s+(?:keyword|word|text|thing|value|variable|identifier|token|character|char|string)$',
        '', text, flags=re.IGNORECASE
    ).strip()
    return text
