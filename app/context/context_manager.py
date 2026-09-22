import os
from pathlib import Path
from typing import Optional
import win32gui
import win32process

from app.clipboard.manager import WindowsClipboardManager
from app.core.models import ScreenContext
from app.filesystem.paths import WindowsPathResolver
from app.logging.logger import logger


class WindowsContextManager:
    """
    Captures real-time Windows application context:
    focused window, process name, active Explorer path, VS Code file/workspace, and clipboard.
    """

    def __init__(self):
        self.path_resolver = WindowsPathResolver()
        self.clipboard = WindowsClipboardManager()

    def capture_context(self) -> ScreenContext:
        """Inspects current desktop state and returns a populated ScreenContext."""
        hwnd = win32gui.GetForegroundWindow()
        window_title = ""
        process_name = "Unknown"
        pid = 0

        if hwnd:
            try:
                window_title = win32gui.GetWindowText(hwnd) or ""
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                try:
                    import win32api
                    import win32con
                    import win32process as wproc
                    handle = win32api.OpenProcess(win32con.PROCESS_QUERY_INFORMATION | win32con.PROCESS_VM_READ, False, pid)
                    modules = wproc.EnumProcessModules(handle)
                    if modules:
                        process_name = os.path.basename(wproc.GetModuleFileNameEx(handle, modules[0]))
                    win32api.CloseHandle(handle)
                except Exception:
                    pass
            except Exception as e:
                logger.debug(f"Error inspecting foreground window: {e}")

        # Active File Explorer path (via COM)
        explorer_path = None
        if "explorer" in process_name.lower() or "folder" in window_title.lower():
            exp_p = self.path_resolver.get_active_explorer_path()
            if exp_p:
                explorer_path = str(exp_p)

        # VS Code context — use VSCodeAdapter (IPC + window-title fallback)
        vscode_file = None
        vscode_line = None
        vscode_workspace = None
        try:
            from app.editor.vscode_adapter import VSCodeAdapter
            from app.ipc.server import ipc_server
            adapter = VSCodeAdapter()
            active_vsc_file = adapter.get_active_file()
            if active_vsc_file:
                vscode_file = str(active_vsc_file)
            vscode_line = ipc_server.state.cursor_line or None
            ws = ipc_server.state.workspace_folder or adapter.get_workspace()
            vscode_workspace = str(ws) if ws else None
        except Exception as e:
            logger.debug(f"VS Code context detection failed: {e}")

        # Truncated clipboard preview
        clip = self.clipboard.get_text()
        clip_preview = clip[:400] if clip else None

        context = ScreenContext(
            active_app=process_name,
            active_window_title=window_title,
            window_handle=hwnd,
            process_id=pid,
            explorer_path=explorer_path,
            vscode_file=vscode_file,
            vscode_line=vscode_line,
            vscode_workspace=vscode_workspace,
            clipboard_text=clip_preview
        )

        return context
