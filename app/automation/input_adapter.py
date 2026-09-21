import time
from typing import List, Optional
import pyautogui

from app.logging.logger import logger

# Safety fail-safe: moving mouse to corner aborts automation
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.05


class WindowsInputAdapter:
    """
    Controlled Windows mouse and keyboard automation.
    Serves as fallback when direct API hooks are unavailable.
    """

    @staticmethod
    def type_text(text: str, interval: float = 0.01) -> None:
        """Types unicode text safely via clipboard or write."""
        if not text:
            return
        try:
            # PyAutoGUI write doesn't always handle complex unicode cleanly;
            # For multiline or unicode, copy & paste is vastly more reliable on Windows
            if any(ord(c) > 127 or c == '\n' for c in text):
                import pyperclip
                old_clip = pyperclip.paste()
                pyperclip.copy(text)
                pyautogui.hotkey("ctrl", "v")
                time.sleep(0.05)
                # optionally restore old clip if short
            else:
                pyautogui.write(text, interval=interval)
        except Exception as e:
            logger.error(f"InputAdapter type_text error: {e}")

    @staticmethod
    def press_key(key: str) -> None:
        """Presses a single key (e.g. 'enter', 'tab', 'esc')."""
        try:
            pyautogui.press(key)
        except Exception as e:
            logger.error(f"InputAdapter press_key error: {e}")

    @staticmethod
    def hotkey(keys: List[str]) -> None:
        """Executes a key combination (e.g. ['ctrl', 'shift', 'p'])."""
        try:
            # Convert Mac 'cmd' to Windows 'ctrl' if any slipped through
            mapped_keys = ['ctrl' if k.lower() == 'cmd' else k for k in keys]
            pyautogui.hotkey(*mapped_keys)
        except Exception as e:
            logger.error(f"InputAdapter hotkey error: {e}")

    @staticmethod
    def click_cursor() -> None:
        """Clicks at the current mouse position."""
        pyautogui.click()

    @staticmethod
    def double_click_cursor() -> None:
        """Double clicks at the current mouse position."""
        pyautogui.doubleClick()

    @staticmethod
    def right_click_cursor() -> None:
        """Right clicks at the current mouse position."""
        pyautogui.rightClick()

    @staticmethod
    def scroll(direction: str = "down", amount: int = 5) -> None:
        """Scrolls vertically."""
        clicks = amount * 120
        if direction.lower() == "down":
            pyautogui.scroll(-clicks)
        else:
            pyautogui.scroll(clicks)

    # Standard Windows edit shortcuts
    @staticmethod
    def copy() -> None:
        pyautogui.hotkey("ctrl", "c")

    @staticmethod
    def paste() -> None:
        pyautogui.hotkey("ctrl", "v")

    @staticmethod
    def select_all() -> None:
        pyautogui.hotkey("ctrl", "a")

    @staticmethod
    def undo() -> None:
        pyautogui.hotkey("ctrl", "z")

    @staticmethod
    def redo() -> None:
        pyautogui.hotkey("ctrl", "y")

    @staticmethod
    def save() -> None:
        pyautogui.hotkey("ctrl", "s")
