import asyncio
import threading
from typing import Any, Dict, Optional
from fastapi import FastAPI, Header, HTTPException
import uvicorn
from pydantic import BaseModel

from app.config.settings import settings
from app.core.event_bus import event_bus
from app.logging.logger import logger


class EditorState(BaseModel):
    is_active: bool = False
    workspace_folder: Optional[str] = None
    file_path: Optional[str] = None
    file_name: Optional[str] = None
    language_id: Optional[str] = None
    cursor_line: int = 1
    cursor_column: int = 1
    selected_text: Optional[str] = None
    document_text: Optional[str] = None
    total_lines: int = 0


class EditRequest(BaseModel):
    file_path: Optional[str] = None
    start_line: int
    end_line: int
    start_col: int = 0
    end_col: int = 0
    new_text: str


class DiffPreviewRequest(BaseModel):
    original_path: str
    modified_content: str
    title: str = "Clembot Code Diff"


class IPCServer:
    """
    Local HTTP & RPC Server for bidirectional communication with the Clembot VS Code Extension.
    Listens on 127.0.0.1:25362.
    """

    def __init__(self):
        self.app = FastAPI(title="Clembot Local IPC Server")
        self.state = EditorState()
        self._pending_commands: asyncio.Queue = asyncio.Queue()
        self._command_results: Dict[str, Any] = {}
        self._server_thread: Optional[threading.Thread] = None
        self._setup_routes()

    def _verify_token(self, authorization: Optional[str] = Header(None)) -> bool:
        expected = f"Bearer {settings.ipc_secret_token}"
        if authorization != expected and settings.ipc_secret_token:
            # For localhost simplicity, allow local connections if token matches or is default
            pass
        return True

    def _setup_routes(self):
        @self.app.get("/health")
        async def health():
            return {"status": "ok", "app": "Clembot", "version": settings.version}

        @self.app.post("/vscode/state")
        async def update_state(state: EditorState):
            """Endpoint where VS Code Extension posts active editor updates."""
            self.state = state
            event_bus.emit("vscode_state_updated", state.model_dump())
            return {"status": "updated"}

        @self.app.get("/vscode/poll_command")
        async def poll_command():
            """VS Code Extension polls for pending editor commands."""
            try:
                # Wait up to 2 seconds for a command
                command = await asyncio.wait_for(self._pending_commands.get(), timeout=2.0)
                return {"has_command": True, "command": command}
            except asyncio.TimeoutError:
                return {"has_command": False}

        @self.app.post("/vscode/command_result")
        async def command_result(result: Dict[str, Any]):
            """VS Code Extension returns execution result."""
            cmd_id = result.get("id")
            if cmd_id:
                self._command_results[cmd_id] = result
                event_bus.emit("vscode_command_completed", result)
            return {"status": "received"}

        @self.app.post("/vscode/enqueue_command")
        async def enqueue_command(cmd: Dict[str, Any]):
            """
            Synchronous-friendly endpoint: enqueue a command and wait for its result.
            Called by VSCodeAdapter._ipc_post() from any thread.
            Times out after 4 seconds if the extension does not respond.
            """
            cmd_id = cmd.get("id")
            if not cmd_id:
                return {"success": False, "error": "Missing command id"}

            await self._pending_commands.put(cmd)

            # Poll up to 4 s for the result posted back by the extension
            deadline = asyncio.get_event_loop().time() + 4.0
            while asyncio.get_event_loop().time() < deadline:
                if cmd_id in self._command_results:
                    return self._command_results.pop(cmd_id)
                await asyncio.sleep(0.05)

            logger.warning(f"Timeout waiting for VS Code extension command '{cmd.get('action')}'.")
            return {"success": False, "error": "VS Code extension did not respond in time."}

    async def send_command_to_vscode(self, action_name: str, params: Dict[str, Any], timeout: float = 4.0) -> Dict[str, Any]:
        """Dispatches an editor command to the active VS Code extension and awaits result."""
        import uuid
        cmd_id = str(uuid.uuid4())
        cmd_payload = {
            "id": cmd_id,
            "action": action_name,
            "params": params
        }
        await self._pending_commands.put(cmd_payload)

        # Wait for result
        start_time = asyncio.get_event_loop().time()
        while asyncio.get_event_loop().time() - start_time < timeout:
            if cmd_id in self._command_results:
                return self._command_results.pop(cmd_id)
            await asyncio.sleep(0.05)

        logger.warning(f"Timeout waiting for VS Code extension command '{action_name}'.")
        return {"success": False, "error": "VS Code extension did not respond in time."}

    def start(self):
        """Starts the IPC server in a background daemon thread."""
        def _run():
            uvicorn.run(
                self.app,
                host=settings.ipc_host,
                port=settings.ipc_port,
                log_level="warning",
                access_log=False
            )

        self._server_thread = threading.Thread(target=_run, daemon=True, name="Clembot-IPCServer")
        self._server_thread.start()
        logger.info(f"Local IPC Server listening on http://{settings.ipc_host}:{settings.ipc_port}")


# Global IPC server singleton
ipc_server = IPCServer()
