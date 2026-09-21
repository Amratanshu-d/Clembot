import ctypes
from datetime import datetime
from pathlib import Path
from typing import Optional
import pyautogui

from app.filesystem.paths import WindowsPathResolver
from app.logging.logger import logger


class WindowsSystemControls:
    """
    Windows system utilities: volume, screenshots, and system state.
    """

    # Virtual key codes for volume control
    VK_VOLUME_MUTE = 0xAD
    VK_VOLUME_DOWN = 0xAE
    VK_VOLUME_UP = 0xAF
    KEYEVENTF_EXTENDEDKEY = 0x0001
    KEYEVENTF_KEYUP = 0x0002

    @classmethod
    def _send_key(cls, vk_code: int) -> None:
        ctypes.windll.user32.keybd_event(vk_code, 0, cls.KEYEVENTF_EXTENDEDKEY, 0)
        ctypes.windll.user32.keybd_event(vk_code, 0, cls.KEYEVENTF_EXTENDEDKEY | cls.KEYEVENTF_KEYUP, 0)

    @classmethod
    def volume_up(cls, steps: int = 5) -> str:
        """Increases volume by specified steps."""
        for _ in range(steps):
            cls._send_key(cls.VK_VOLUME_UP)
        return "Volume increased."

    @classmethod
    def volume_down(cls, steps: int = 5) -> str:
        """Decreases volume by specified steps."""
        for _ in range(steps):
            cls._send_key(cls.VK_VOLUME_DOWN)
        return "Volume decreased."

    @classmethod
    def volume_mute_toggle(cls) -> str:
        """Toggles volume mute."""
        cls._send_key(cls.VK_VOLUME_MUTE)
        return "Mute toggled."

    @classmethod
    def capture_screenshot(cls, destination_folder: Optional[Path] = None) -> tuple[Path, str]:
        """
        Captures full-screen screenshot and saves to Pictures/Screenshots or Desktop.
        Returns (saved_path, confirmation_message).
        """
        if destination_folder is None:
            standard = WindowsPathResolver.get_standard_folders()
            screenshots_dir = standard["Pictures"] / "Screenshots"
            if not screenshots_dir.exists():
                screenshots_dir.mkdir(parents=True, exist_ok=True)
            target_dir = screenshots_dir if screenshots_dir.is_dir() else standard["Desktop"]
        else:
            target_dir = destination_folder

        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"Screenshot_{timestamp}.png"
        filepath = target_dir / filename

        screenshot = pyautogui.screenshot()
        screenshot.save(str(filepath))
        logger.info(f"Screenshot saved to: {filepath}")
        return filepath, f"Screenshot saved to {filepath.name}."
