import os
import re
from pathlib import Path
from typing import Dict, List, Optional
import win32api

from app.logging.logger import logger


class WindowsPathResolver:
    """
    Dynamically resolves Windows known folders, system drives, and relative folder names
    without hardcoding usernames or static drive letters.
    """

    FOLDER_ALIASES: Dict[str, str] = {
        "desktop": "Desktop",
        "my desktop": "Desktop",
        "documents": "Documents",
        "my documents": "Documents",
        "my documents folder": "Documents",
        "downloads": "Downloads",
        "my downloads": "Downloads",
        "my downloads folder": "Downloads",
        "pictures": "Pictures",
        "my pictures": "Pictures",
        "photos": "Pictures",
        "videos": "Videos",
        "my videos": "Videos",
        "movies": "Videos",
        "music": "Music",
        "my music": "Music",
        "home": "Home",
        "user profile": "Home",
        "onedrive": "OneDrive",
        "my onedrive": "OneDrive",
        "c drive": "C:\\",
        "drive c": "C:\\",
        "c:": "C:\\",
        "root": "C:\\",
    }

    @classmethod
    def get_user_home(cls) -> Path:
        """Returns current user's profile directory (%USERPROFILE%)."""
        user_profile = os.environ.get("USERPROFILE")
        if user_profile and os.path.isdir(user_profile):
            return Path(user_profile)
        return Path.home()

    @classmethod
    def get_standard_folders(cls) -> Dict[str, Path]:
        """Maps canonical folder names to their resolved Path on the current Windows machine."""
        home = cls.get_user_home()
        folders = {
            "Home": home,
            "Desktop": home / "Desktop",
            "Documents": home / "Documents",
            "Downloads": home / "Downloads",
            "Pictures": home / "Pictures",
            "Videos": home / "Videos",
            "Music": home / "Music",
        }

        # Check OneDrive path if configured
        onedrive = os.environ.get("OneDrive") or os.environ.get("OneDriveConsumer") or os.environ.get("OneDriveCommercial")
        if onedrive and os.path.isdir(onedrive):
            folders["OneDrive"] = Path(onedrive)
        elif (home / "OneDrive").is_dir():
            folders["OneDrive"] = home / "OneDrive"

        return folders

    @classmethod
    def get_available_drives(cls) -> List[str]:
        """Returns a list of all mounted drive letters (e.g. ['C:\\', 'D:\\'])."""
        drives = []
        try:
            bitmask = win32api.GetLogicalDrives()
            for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
                if bitmask & 1:
                    drives.append(f"{letter}:\\")
                bitmask >>= 1
        except Exception as e:
            logger.debug(f"win32api GetLogicalDrives failed, fallback to drive check: {e}")
            for letter in "CDEFGHIJKLMNOPQRSTUVWXYZ":
                drive_path = f"{letter}:\\"
                if os.path.exists(drive_path):
                    drives.append(drive_path)
        return drives

    @classmethod
    def get_active_explorer_path(cls) -> Optional[Path]:
        """
        Queries Windows File Explorer via COM to find the folder path currently open
        in the focused Explorer window.
        """
        try:
            import win32com.client
            import pythoncom
            pythoncom.CoInitialize()

            shell = win32com.client.Dispatch("Shell.Application")
            windows = shell.Windows()

            # The focused window may be an explorer window
            import win32gui
            foreground_hwnd = win32gui.GetForegroundWindow()

            for window in windows:
                try:
                    if window.HWND == foreground_hwnd or foreground_hwnd == 0:
                        location_url = window.LocationURL
                        if location_url and location_url.startswith("file:///"):
                            raw_path = location_url[8:].replace("/", "\\")
                            # Handle URL-encoded characters like %20
                            from urllib.parse import unquote
                            unquoted_path = unquote(raw_path)
                            if os.path.isdir(unquoted_path):
                                return Path(unquoted_path)
                except Exception:
                    continue

            # If foreground window was not an Explorer window, return top explorer window if any
            for window in windows:
                try:
                    location_url = window.LocationURL
                    if location_url and location_url.startswith("file:///"):
                        from urllib.parse import unquote
                        unquoted_path = unquote(location_url[8:].replace("/", "\\"))
                        if os.path.isdir(unquoted_path):
                            return Path(unquoted_path)
                except Exception:
                    continue

        except Exception as e:
            logger.debug(f"Could not retrieve active File Explorer path: {e}")
        return None

    @classmethod
    def resolve_path(cls, raw: str, base_context: Optional[Path] = None, context_base: Optional[Path] = None) -> Path:
        r"""
        Intelligently resolves a user-spoken string or relative path to an absolute Path.
        Examples:
        - "Downloads" -> C:\Users\Username\Downloads
        - "Projects on Desktop" -> C:\Users\Username\Desktop\Projects
        - "notes.txt" -> base_context / notes.txt (or Desktop / notes.txt)
        - "C:\temp\file.txt" -> C:\temp\file.txt
        """
        active_base = base_context or context_base
        raw_clean = raw.strip()
        lower = raw_clean.lower()

        standard_folders = cls.get_standard_folders()

        # Direct match with standard folders
        if lower in cls.FOLDER_ALIASES:
            canonical = cls.FOLDER_ALIASES[lower]
            if canonical in standard_folders:
                return standard_folders[canonical]
            if canonical.endswith(":\\") and os.path.exists(canonical):
                return Path(canonical)

        # Match phrases like "Projects on Desktop" or "resume in Downloads"
        loc_match = re.search(r'^(.*?)\s+(?:on|in|under|inside)\s+(desktop|downloads|documents|pictures|videos|music|onedrive)$', lower)
        if loc_match:
            subpath = loc_match.group(1).strip()
            loc_name = loc_match.group(2).strip()
            canonical_loc = cls.FOLDER_ALIASES.get(loc_name, "Desktop")
            parent_dir = standard_folders.get(canonical_loc, standard_folders["Desktop"])
            return parent_dir / subpath

        # Expand Windows environment variables (e.g. %USERPROFILE%\foo, %APPDATA%)
        expanded = os.path.expandvars(raw_clean)

        # Direct absolute path
        p = Path(expanded)
        if p.is_absolute():
            return p

        # If user refers to "here" or "this folder", use active Explorer path or base_context
        if lower in ["here", "this folder", "current folder"]:
            explorer_path = cls.get_active_explorer_path()
            if explorer_path:
                return explorer_path
            if active_base:
                return active_base
            return standard_folders["Desktop"]

        # If base context is provided (e.g. from conversational memory), use it if item exists there
        if active_base and active_base.is_dir():
            cand = active_base / raw_clean
            if cand.exists():
                return cand

        # Check active Explorer window if item exists there
        explorer_path = cls.get_active_explorer_path()
        if explorer_path and explorer_path.is_dir():
            cand = explorer_path / raw_clean
            if cand.exists():
                return cand

        # Check standard user locations if file exists there
        for folder_key in ["Desktop", "Downloads", "Documents"]:
            if folder_key in standard_folders:
                cand = standard_folders[folder_key] / raw_clean
                if cand.exists():
                    return cand

        # Default fallback: active_base / raw_clean (or Desktop / raw_clean)
        if active_base and active_base.is_dir():
            return active_base / raw_clean
        return standard_folders["Desktop"] / raw_clean

    resolve = resolve_path
