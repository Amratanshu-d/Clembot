import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class ConversationTurn:
    timestamp: datetime
    speaker: str  # "user" or "clembot"
    text: str
    intent: Optional[str] = None
    target_path: Optional[str] = None
    target_app: Optional[str] = None
    target_file: Optional[str] = None


class ConversationalMemory:
    """
    Maintains short-term conversational context and resolves pronouns and directional references.
    Examples: "there" -> last visited folder, "that file" -> last opened file.
    """

    def __init__(self, max_history: int = 20):
        self.history: List[ConversationTurn] = []
        self.max_history = max_history
        self.last_folder: Optional[Path] = None
        self.last_file: Optional[Path] = None
        self.last_app: Optional[str] = None
        self.last_function: Optional[str] = None

    def add_user_turn(self, text: str) -> None:
        turn = ConversationTurn(
            timestamp=datetime.now(),
            speaker="user",
            text=text
        )
        self.history.append(turn)
        if len(self.history) > self.max_history:
            self.history.pop(0)

    def add_clembot_turn(
        self,
        text: str,
        intent: Optional[str] = None,
        target_path: Optional[str] = None,
        target_app: Optional[str] = None,
        target_file: Optional[str] = None
    ) -> None:
        turn = ConversationTurn(
            timestamp=datetime.now(),
            speaker="clembot",
            text=text,
            intent=intent,
            target_path=target_path,
            target_app=target_app,
            target_file=target_file
        )
        self.history.append(turn)
        if len(self.history) > self.max_history:
            self.history.pop(0)

        # Update cached entity references
        if target_path:
            p = Path(target_path)
            if p.is_dir():
                self.last_folder = p
            else:
                self.last_file = p
                self.last_folder = p.parent

        if target_file:
            self.last_file = Path(target_file)
            if self.last_file.parent:
                self.last_folder = self.last_file.parent

        if target_app:
            self.last_app = target_app

    def resolve_contextual_references(self, command: str) -> str:
        """
        Replaces contextual references like 'there', 'that folder', 'that file'
        with the concrete entities from memory.
        """
        resolved = command

        # Resolve "there" or "in there" to the last visited folder
        if self.last_folder:
            folder_str = str(self.last_folder)
            resolved = re.sub(r'\b(?:in\s+)?there\b', lambda m: f"in {folder_str}", resolved, flags=re.IGNORECASE)
            resolved = re.sub(r'\bthat\s+folder\b', lambda m: f"folder {folder_str}", resolved, flags=re.IGNORECASE)

        # Resolve "that file" or "it" when a file was recently discussed
        if self.last_file:
            file_str = str(self.last_file)
            resolved = re.sub(r'\bthat\s+file\b', lambda m: f"file {file_str}", resolved, flags=re.IGNORECASE)
            # Only replace " it " if it clearly refers to an action on the file (e.g. "delete it", "open it")
            resolved = re.sub(r'\b(delete|open|rename|copy|move|run)\s+it\b', lambda m: f"{m.group(1)} {file_str}", resolved, flags=re.IGNORECASE)

        return resolved

    def get_recent_history(self, limit: int = 6) -> List[Dict[str, str]]:
        """Returns recent conversation turns formatted for LLM context."""
        recent = self.history[-limit:] if len(self.history) > limit else list(self.history)
        return [{"role": "user" if t.speaker == "user" else "assistant", "content": t.text} for t in recent]

    def clear(self) -> None:
        self.history.clear()
        self.last_folder = None
        self.last_file = None
        self.last_app = None
        self.last_function = None
