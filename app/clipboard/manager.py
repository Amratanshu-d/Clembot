from pathlib import Path
from typing import Optional
import pyperclip

from app.logging.logger import logger


class WindowsClipboardManager:
    """
    Manages Windows clipboard operations (text copy, paste, inspection, save to file).
    """

    @staticmethod
    def copy_text(text: str) -> str:
        """Copies text to the system clipboard."""
        pyperclip.copy(text)
        logger.info(f"Copied {len(text)} characters to clipboard.")
        return "Copied to clipboard."

    @staticmethod
    def get_text() -> str:
        """Retrieves text from the clipboard."""
        try:
            return pyperclip.paste() or ""
        except Exception as e:
            logger.debug(f"Error reading clipboard: {e}")
            return ""

    @staticmethod
    def clear() -> str:
        """Clears the clipboard."""
        try:
            pyperclip.copy("")
            return "Clipboard cleared."
        except Exception as e:
            logger.error(f"Error clearing clipboard: {e}")
            return "Could not clear clipboard."

    @staticmethod
    def save_to_file(filepath: Path) -> str:
        """Saves current clipboard text to a destination file."""
        text = pyperclip.paste()
        if not text:
            return "Clipboard is empty; nothing to save."

        filepath.parent.mkdir(parents=True, exist_ok=True)
        filepath.write_text(text, encoding="utf-8")
        logger.info(f"Saved clipboard contents to {filepath}")
        return f"Saved clipboard contents to {filepath.name}."
