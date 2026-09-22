import os
import shutil
import subprocess
import urllib.parse
from typing import Dict, Optional
import pyautogui

from app.config.settings import settings
from app.logging.logger import logger
from app.windows.apps import WindowsAppCatalog


class BrowserController:
    """
    Controls web browsing on Windows across Chrome, Edge, and Firefox.
    Handles URL navigation, search engines (Google, YouTube, GitHub, Bing, DDG), and tab shortcuts.
    """

    SEARCH_ENGINES: Dict[str, str] = {
        "google": "https://www.google.com/search?q={query}",
        "youtube": "https://www.youtube.com/results?search_query={query}",
        "github": "https://github.com/search?q={query}",
        "bing": "https://www.bing.com/search?q={query}",
        "duckduckgo": "https://duckduckgo.com/?q={query}",
    }

    WEB_DESTINATIONS: Dict[str, str] = {
        "github": "https://github.com",
        "youtube": "https://www.youtube.com",
        "gmail": "https://mail.google.com",
        "google docs": "https://docs.google.com",
        "docs": "https://docs.google.com",
        "google sheets": "https://sheets.google.com",
        "sheets": "https://sheets.google.com",
        "google drive": "https://drive.google.com",
        "drive": "https://drive.google.com",
        "google chat": "https://chat.google.com",
        "chatgpt": "https://chatgpt.com",
        "gemini": "https://gemini.google.com",
        "claude": "https://claude.ai",
        "canva": "https://www.canva.com",
        "whatsapp": "https://web.whatsapp.com",
        "whatsapp web": "https://web.whatsapp.com",
        "netflix": "https://www.netflix.com",
        "amazon": "https://www.amazon.com",
        "google": "https://www.google.com",
        "reddit": "https://www.reddit.com",
        "stackoverflow": "https://stackoverflow.com",
        "twitter": "https://x.com",
        "x": "https://x.com",
        "linkedin": "https://www.linkedin.com",
    }

    def __init__(self):
        self.apps = WindowsAppCatalog()

    def _get_browser_executable(self, preferred_browser: Optional[str] = None) -> Optional[str]:
        """Finds the browser executable."""
        browser_name = preferred_browser or settings.default_browser
        browser_name = browser_name.lower().strip()

        def _resolve_target(name: str) -> Optional[str]:
            res = self.apps.find_executable(name)
            if res:
                return res[0] if isinstance(res, tuple) else res
            return None

        if browser_name in ["chrome", "google chrome"]:
            return _resolve_target("chrome")
        elif browser_name in ["edge", "microsoft edge"]:
            return _resolve_target("edge")
        elif browser_name in ["firefox", "mozilla firefox"]:
            return _resolve_target("firefox")
        else:
            # Fallback to any installed browser
            for candidate in ["chrome", "edge", "firefox"]:
                exe = _resolve_target(candidate)
                if exe:
                    return exe
        return None

    def open_url(self, raw_url: str, browser: Optional[str] = None) -> str:
        """
        Navigates to the specified URL using the requested or default browser.
        """
        url = raw_url.strip()
        if not url.startswith(("http://", "https://")):
            url = f"https://{url}"

        exe = self._get_browser_executable(browser)
        if exe:
            try:
                subprocess.Popen([exe, url])
                return f"Opening {url}."
            except Exception as e:
                logger.error(f"Failed to launch browser executable {exe}: {e}")

        # Fallback to Windows default handler
        os.startfile(url)
        return f"Opening {url}."

    def search_web(self, query: str, engine: Optional[str] = None, browser: Optional[str] = None) -> str:
        """
        Executes a web search on Google, YouTube, GitHub, Bing, or DuckDuckGo.
        """
        q = query.strip()
        if not q:
            return "Please provide a search term."

        engine_key = (engine or settings.default_search_engine).lower().strip()
        url_template = self.SEARCH_ENGINES.get(engine_key, self.SEARCH_ENGINES["google"])
        
        encoded_query = urllib.parse.quote_plus(q)
        target_url = url_template.format(query=encoded_query)

        self.open_url(target_url, browser)
        engine_name = engine_key.capitalize()
        return f"Searching {engine_name} for '{q}'."

    def open_web_destination(self, name: str, browser: Optional[str] = None) -> Optional[str]:
        """Opens a well-known site like GitHub, YouTube, or Gmail."""
        norm_name = name.lower().strip()
        if norm_name in self.WEB_DESTINATIONS:
            url = self.WEB_DESTINATIONS[norm_name]
            return self.open_url(url, browser)
        return None

    # Browser tab actions
    @staticmethod
    def new_tab() -> str:
        pyautogui.hotkey("ctrl", "t")
        return "Opened new tab."

    @staticmethod
    def close_tab() -> str:
        pyautogui.hotkey("ctrl", "w")
        return "Closed tab."

    @staticmethod
    def next_tab() -> str:
        pyautogui.hotkey("ctrl", "tab")
        return "Switched to next tab."

    @staticmethod
    def previous_tab() -> str:
        pyautogui.hotkey("ctrl", "shift", "tab")
        return "Switched to previous tab."

    @staticmethod
    def reopen_tab() -> str:
        pyautogui.hotkey("ctrl", "shift", "t")
        return "Reopened closed tab."

    @staticmethod
    def reload() -> str:
        pyautogui.hotkey("ctrl", "r")
        return "Reloading page."

    @staticmethod
    def focus_address_bar() -> str:
        pyautogui.hotkey("ctrl", "l")
        return "Address bar focused."
