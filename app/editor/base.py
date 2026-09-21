from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, Optional, Tuple


class EditorAdapter(ABC):
    """Abstract interface for code editor integrations."""

    @abstractmethod
    def is_available(self) -> bool:
        """Returns True if the editor or its bridge is active."""
        pass

    @abstractmethod
    def get_active_file(self) -> Optional[Path]:
        """Returns path of currently open file."""
        pass

    @abstractmethod
    def read_document(self, file_path: Optional[Path] = None) -> Optional[str]:
        """Reads document content."""
        pass

    @abstractmethod
    def jump_to_line(self, line_number: int) -> bool:
        """Navigates cursor to a specific line."""
        pass

    @abstractmethod
    def apply_edit(
        self,
        file_path: Path,
        start_line: int,
        end_line: int,
        new_text: str,
        start_col: int = 0,
        end_col: int = 0
    ) -> bool:
        """Applies a targeted range replacement."""
        pass

    @abstractmethod
    def save(self) -> bool:
        """Saves current document."""
        pass

    @abstractmethod
    def run_code(self) -> bool:
        """Runs the active file in terminal."""
        pass

    @abstractmethod
    def undo(self) -> bool:
        """Reverts the last edit."""
        pass
