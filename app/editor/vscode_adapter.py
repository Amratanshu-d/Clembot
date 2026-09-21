"""
app/editor/vscode_adapter.py

VS Code integration with 3-layer file detection:
  1. IPC extension (live cursor + full path) — best
  2. VS Code globalStorage/storage.json workspace + window title filename — no extension needed
  3. Last-known path cache — per-session fallback

All edit operations work directly on disk, so no extension is required.
"""

import ctypes
import ctypes.wintypes as wt
import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import unquote, urlparse

import httpx

from app.editor.base import EditorAdapter
from app.ipc.server import ipc_server
from app.logging.logger import logger

_IPC_BASE = "http://127.0.0.1:25362"


# ---------------------------------------------------------------------------
# IPC helper
# ---------------------------------------------------------------------------

def _ipc_post(path: str, payload: Dict[str, Any], timeout: float = 4.0) -> Dict[str, Any]:
    """Synchronous HTTP POST to the IPC server (avoids asyncio cross-thread deadlock)."""
    try:
        resp = httpx.post(f"{_IPC_BASE}{path}", json=payload, timeout=timeout)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logger.debug(f"IPC HTTP call to {path} failed: {e}")
        return {"success": False, "error": str(e)}


# ---------------------------------------------------------------------------
# VS Code state readers
# ---------------------------------------------------------------------------

def _get_vscode_workspace_from_storage() -> Optional[Path]:
    """
    Read VS Code's globalStorage/storage.json to find the current workspace folder.
    Returns the workspace Path or None.
    """
    appdata = os.environ.get("APPDATA", "")
    if not appdata:
        return None

    for variant in ("Code", "Code - Insiders", "VSCodium"):
        storage = Path(appdata) / variant / "User" / "globalStorage" / "storage.json"
        if not storage.is_file():
            continue
        try:
            data = json.loads(storage.read_text(encoding="utf-8", errors="replace"))
            ws_state = data.get("windowsState", {})
            last = ws_state.get("lastActiveWindow", {})
            folder_uri = last.get("folder") or last.get("workspace", {}).get("configPath")
            if folder_uri:
                return _uri_to_path(folder_uri)
        except Exception as e:
            logger.debug(f"Failed to parse VS Code storage.json at {storage}: {e}")

    return None


def _uri_to_path(uri: str) -> Optional[Path]:
    """Convert a VS Code file:// URI (possibly URL-encoded) to a Path."""
    try:
        parsed = urlparse(unquote(uri))
        if parsed.scheme == "file":
            p = parsed.path
            # Windows: /c:/Users/... → c:/Users/...
            if p.startswith("/") and len(p) > 2 and p[2] == ":":
                p = p[1:]
            return Path(p)
    except Exception:
        pass
    return None


def _get_vscode_window_titles() -> List[str]:
    """
    Enumerate all window titles belonging to a VS Code process using
    pure ctypes (avoids the win32gui EnumWindows callback-exception crash).
    """
    titles: List[str] = []
    WNDENUMPROC = ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)

    def _callback(hwnd: int, _: int) -> bool:
        try:
            # Quick visibility check
            if not ctypes.windll.user32.IsWindowVisible(hwnd):
                return True
            buf = ctypes.create_unicode_buffer(512)
            ctypes.windll.user32.GetWindowTextW(hwnd, buf, 512)
            title = buf.value
            if title and "Visual Studio Code" in title:
                titles.append(title)
        except Exception:
            pass
        return True

    ctypes.windll.user32.EnumWindows(WNDENUMPROC(_callback), 0)
    return titles


def _parse_filename_from_title(title: str) -> Optional[str]:
    """
    Parse the open filename from a VS Code window title.

    Formats handled:
      main.py — myproject — Visual Studio Code
      ● main.py — myproject — Visual Studio Code   (unsaved changes)
      myproject — Visual Studio Code               (no file open, folder only)
      Welcome — Visual Studio Code
    """
    # Strip unsaved indicator (● or •)
    title = re.sub(r"^[●•\u25cf\*]\s*", "", title).strip()

    if "Visual Studio Code" not in title:
        return None

    # Split on em-dash, en-dash, or " - "
    parts = re.split(r"\s*[—–]\s*|\s+-\s+", title)
    if not parts:
        return None

    candidate = parts[0].strip()

    # Must look like a filename (has a dot, not a generic word)
    if "." in candidate and candidate not in ("Visual Studio Code", "Welcome", "Untitled"):
        return candidate

    return None


# ---------------------------------------------------------------------------
# Main adapter class
# ---------------------------------------------------------------------------

class VSCodeAdapter(EditorAdapter):
    """
    VS Code integration with 3-layer active-file detection:
      1. IPC extension state (live)
      2. globalStorage/storage.json workspace + window title filename
      3. Per-session path cache
    """

    # Class-level cache — persists across method calls within one session
    _cached_file: Optional[Path] = None
    _cached_workspace: Optional[Path] = None

    def is_available(self) -> bool:
        return ipc_server.state.is_active

    # ------------------------------------------------------------------
    # File detection
    # ------------------------------------------------------------------

    def _resolve_from_storage_and_title(self) -> Optional[Path]:
        """
        Step 2: read workspace from storage.json + filename from window title,
        search only inside the workspace folder (fast, bounded).
        """
        # Get workspace root
        workspace = _get_vscode_workspace_from_storage()
        if workspace:
            VSCodeAdapter._cached_workspace = workspace

        # Parse filename from window title
        titles = _get_vscode_window_titles()
        filename: Optional[str] = None
        for t in titles:
            fn = _parse_filename_from_title(t)
            if fn:
                filename = fn
                break

        if not filename:
            logger.debug("No filename found in VS Code window titles.")
            return None

        logger.debug(f"VS Code title suggests open file: '{filename}', workspace: {workspace}")

        # Search: workspace first (fast), then user home subfolders (depth-limited)
        search_roots: List[Path] = []
        if workspace and workspace.is_dir():
            search_roots.append(workspace)
        if VSCodeAdapter._cached_workspace and VSCodeAdapter._cached_workspace.is_dir():
            search_roots.append(VSCodeAdapter._cached_workspace)
        if VSCodeAdapter._cached_file:
            search_roots.append(VSCodeAdapter._cached_file.parent)

        # Add common user folders (limited depth)
        home = Path.home()
        for sub in ("Desktop", "Documents", "Downloads", "Projects", "Code", "dev", "src"):
            p = home / sub
            if p.is_dir():
                search_roots.append(p)

        # Deduplicate
        seen = set()
        unique_roots = []
        for r in search_roots:
            if r not in seen:
                seen.add(r)
                unique_roots.append(r)

        for root in unique_roots:
            try:
                # Depth-limited search (max 4 levels to stay fast)
                for match in _rglob_bounded(root, filename, max_depth=4):
                    logger.info(f"Resolved VS Code active file: {match}")
                    VSCodeAdapter._cached_file = match
                    return match
            except (PermissionError, OSError):
                pass

        return None

    def get_active_file(self) -> Optional[Path]:
        """
        Returns the currently focused file in VS Code.
        Layer 1 → IPC; Layer 2 → storage+title; Layer 3 → cache.
        """
        # Layer 1: IPC extension (most accurate)
        if ipc_server.state.is_active and ipc_server.state.file_path:
            p = Path(ipc_server.state.file_path)
            if p.is_file():
                VSCodeAdapter._cached_file = p
                return p

        # Layer 2: storage.json + window title
        found = self._resolve_from_storage_and_title()
        if found:
            return found

        # Layer 3: stale cache
        if VSCodeAdapter._cached_file and VSCodeAdapter._cached_file.is_file():
            logger.debug(f"Using cached VS Code file: {VSCodeAdapter._cached_file}")
            return VSCodeAdapter._cached_file

        return None

    def get_workspace(self) -> Optional[Path]:
        """Returns the current VS Code workspace folder."""
        if ipc_server.state.workspace_folder:
            return Path(ipc_server.state.workspace_folder)
        return _get_vscode_workspace_from_storage() or VSCodeAdapter._cached_workspace

    # ------------------------------------------------------------------
    # Document content
    # ------------------------------------------------------------------

    def read_document(self, file_path: Optional[Path] = None) -> Optional[str]:
        """Reads document content: IPC memory → explicit path → active file → disk."""
        # IPC has live in-memory content (most up-to-date, includes unsaved changes)
        if file_path is None and ipc_server.state.document_text:
            return ipc_server.state.document_text

        target = file_path or self.get_active_file()
        if target and target.is_file():
            try:
                return target.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                return target.read_text(encoding="cp1252", errors="replace")
            except Exception as e:
                logger.error(f"Failed to read {target}: {e}")
        return None

    # ------------------------------------------------------------------
    # Editor commands
    # ------------------------------------------------------------------

    def jump_to_line(self, line_number: int) -> bool:
        if self.is_available():
            import uuid
            res = _ipc_post("/vscode/enqueue_command", {
                "id": str(uuid.uuid4()), "action": "jump_to_line",
                "params": {"line_number": line_number}
            })
            if res.get("success"):
                return True

        active_file = self.get_active_file()
        if active_file:
            try:
                subprocess.Popen(["code", "--reuse-window", "--goto",
                                  f"{active_file}:{line_number}"], shell=True)
                return True
            except Exception as e:
                logger.error(f"CLI jump failed: {e}")
        return False

    def open_file(self, file_path: Path, line_number: Optional[int] = None) -> bool:
        """
        Opens / reloads a file in VS Code using --reuse-window so we don't
        spawn a second window after every programmatic edit.
        """
        try:
            cmd = ["code", "--reuse-window"]
            if line_number:
                cmd.extend(["--goto", f"{file_path}:{line_number}"])
            else:
                cmd.append(str(file_path))
            subprocess.Popen(cmd, shell=True)
            VSCodeAdapter._cached_file = file_path
            return True
        except Exception as e:
            logger.error(f"Failed to open {file_path} in VS Code: {e}")
            return False

    def apply_edit(
        self,
        file_path: Path,
        start_line: int,
        end_line: int,
        new_text: str,
        start_col: int = 0,
        end_col: int = 0,
    ) -> bool:
        """IPC first; programmatic file edit as fallback."""
        if self.is_available():
            import uuid
            res = _ipc_post("/vscode/enqueue_command", {
                "id": str(uuid.uuid4()), "action": "apply_edit",
                "params": {
                    "start_line": start_line, "end_line": end_line,
                    "start_col": start_col, "end_col": end_col, "new_text": new_text,
                }
            })
            if res.get("success"):
                return True
            logger.debug(f"IPC apply_edit failed, using file fallback: {res.get('error')}")

        if not file_path.is_file():
            return False
        try:
            bak = file_path.with_suffix(file_path.suffix + ".bak")
            shutil.copy2(file_path, bak)
            raw = file_path.read_bytes()
            try:
                text = raw.decode("utf-8")
            except UnicodeDecodeError:
                text = raw.decode("cp1252", errors="replace")
            lines = text.splitlines(keepends=True)
            s = max(0, start_line - 1)
            e = min(len(lines), end_line)
            # Detect EOL from file
            eol = "\r\n" if text.count("\r\n") >= text.count("\n") - text.count("\r\n") else "\n"
            chunk = new_text.rstrip("\r\n") + eol
            lines[s:e] = [chunk]
            file_path.write_bytes("".join(lines).encode("utf-8"))
            return True
        except Exception as ex:
            logger.error(f"File-level edit failed: {ex}")
            return False

    def save(self) -> bool:
        if self.is_available():
            import uuid
            res = _ipc_post("/vscode/enqueue_command", {
                "id": str(uuid.uuid4()), "action": "save_document", "params": {}
            })
            if res.get("success"):
                return True
        try:
            import pyautogui
            pyautogui.hotkey("ctrl", "s")
            return True
        except Exception:
            pass
        return False

    def run_code(self) -> bool:
        if self.is_available():
            import uuid
            res = _ipc_post("/vscode/enqueue_command", {
                "id": str(uuid.uuid4()), "action": "run_code", "params": {}
            })
            if res.get("success"):
                return True
        active_file = self.get_active_file()
        if active_file and active_file.is_file():
            if active_file.suffix == ".py":
                subprocess.Popen(f'start cmd /k python "{active_file}"', shell=True)
                return True
        return False

    def undo(self) -> bool:
        if self.is_available():
            import uuid
            res = _ipc_post("/vscode/enqueue_command", {
                "id": str(uuid.uuid4()), "action": "undo", "params": {}
            })
            if res.get("success"):
                return True
        active_file = self.get_active_file()
        if active_file:
            bak = active_file.with_suffix(active_file.suffix + ".bak")
            if bak.is_file():
                shutil.copy2(bak, active_file)
                logger.info(f"Restored {active_file} from backup")
                return True
        return False

    def get_vscode_context(self) -> Dict[str, Any]:
        active = self.get_active_file()
        return {
            "active_file": str(active) if active else None,
            "workspace_folder": str(self.get_workspace()) if self.get_workspace() else None,
            "cursor_line": ipc_server.state.cursor_line,
            "ipc_connected": ipc_server.state.is_active,
        }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _rglob_bounded(root: Path, filename: str, max_depth: int) -> List[Path]:
    """Walk `root` up to `max_depth` directory levels looking for `filename`."""
    results: List[Path] = []
    root_str = str(root)
    try:
        for dirpath, dirnames, filenames in os.walk(root_str):
            # Compute current depth relative to root
            depth = dirpath.replace(root_str, "").count(os.sep)
            if filename in filenames:
                results.append(Path(dirpath) / filename)
            if depth >= max_depth:
                dirnames.clear()  # prune — don't descend further
    except (PermissionError, OSError):
        pass
    return results
