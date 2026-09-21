import ctypes
from typing import Optional, Tuple
import win32api
import win32con
import win32gui

from app.logging.logger import logger


class WindowsWindowManager:
    """
    Controls Windows window placement, state (minimize/maximize/restore), and snapping
    using native Windows User32 APIs.
    """

    @staticmethod
    def get_focused_hwnd() -> int:
        """Returns HWND of the currently focused/foreground window."""
        return win32gui.GetForegroundWindow()

    @staticmethod
    def get_screen_dimensions() -> Tuple[int, int]:
        """Returns primary display resolution (width, height)."""
        width = win32api.GetSystemMetrics(win32con.SM_CXSCREEN)
        height = win32api.GetSystemMetrics(win32con.SM_CYSCREEN)
        return width, height

    @staticmethod
    def get_work_area() -> Tuple[int, int, int, int]:
        """Returns usable desktop area excluding taskbar (left, top, right, bottom)."""
        rect = win32gui.SystemParametersInfo(win32con.SPI_GETWORKAREA)
        return rect  # (left, top, right, bottom)

    def minimize_current(self) -> str:
        """Minimizes the currently focused window."""
        hwnd = self.get_focused_hwnd()
        if hwnd:
            win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
            return "Window minimized."
        return "No active window to minimize."

    def maximize_current(self) -> str:
        """Maximizes the currently focused window."""
        hwnd = self.get_focused_hwnd()
        if hwnd:
            win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
            return "Window maximized."
        return "No active window to maximize."

    def restore_current(self) -> str:
        """Restores the currently focused window."""
        hwnd = self.get_focused_hwnd()
        if hwnd:
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            return "Window restored."
        return "No active window to restore."

    def close_current(self) -> str:
        """Closes the currently focused window gracefully."""
        hwnd = self.get_focused_hwnd()
        if hwnd:
            title = win32gui.GetWindowText(hwnd) or "current application"
            win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
            return f"Closed {title}."
        return "No active window to close."

    def snap_left(self) -> str:
        """Snaps the focused window to the left half of the monitor."""
        hwnd = self.get_focused_hwnd()
        if not hwnd:
            return "No active window to move."

        # Ensure restored before positioning
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        left, top, right, bottom = self.get_work_area()
        width = (right - left) // 2
        height = bottom - top

        win32gui.MoveWindow(hwnd, left, top, width, height, True)
        return "Snapped window to left half."

    def snap_right(self) -> str:
        """Snaps the focused window to the right half of the monitor."""
        hwnd = self.get_focused_hwnd()
        if not hwnd:
            return "No active window to move."

        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        left, top, right, bottom = self.get_work_area()
        half_width = (right - left) // 2
        height = bottom - top

        win32gui.MoveWindow(hwnd, left + half_width, top, half_width, height, True)
        return "Snapped window to right half."

    def center_window(self) -> str:
        """Centers the focused window on screen."""
        hwnd = self.get_focused_hwnd()
        if not hwnd:
            return "No active window to center."

        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        w_left, w_top, w_right, w_bottom = self.get_work_area()
        screen_w = w_right - w_left
        screen_h = w_bottom - w_top

        # Default centered size: 70% width and height
        target_w = int(screen_w * 0.7)
        target_h = int(screen_h * 0.7)
        pos_x = w_left + (screen_w - target_w) // 2
        pos_y = w_top + (screen_h - target_h) // 2

        win32gui.MoveWindow(hwnd, pos_x, pos_y, target_w, target_h, True)
        return "Centered window."

    def show_desktop(self) -> str:
        """Minimizes all windows to reveal desktop (Win+D)."""
        import pyautogui
        pyautogui.hotkey("win", "d")
        return "Showing desktop."
