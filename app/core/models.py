import uuid
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class AssistantState(str, Enum):
    IDLE = "IDLE"                            # Deactivated / sleeping
    LISTENING = "LISTENING"                  # Activated, capturing mic audio
    PROCESSING = "PROCESSING"                # Understanding intent / routing
    AWAITING_CONFIRMATION = "AWAITING_CONFIRMATION"  # Asking user to confirm risky action / code edit
    EXECUTING = "EXECUTING"                  # Running actions
    SPEAKING = "SPEAKING"                    # Generating TTS response
    ERROR = "ERROR"                          # An error occurred


class AgentAction(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: str                                # e.g. "open_folder", "create_file", "vscode_patch", "vscode_edit", "web_search"
    app: Optional[str] = None                # e.g. "Google Chrome", "VS Code", "Notepad"
    url: Optional[str] = None                # e.g. "https://github.com"
    text: Optional[str] = None               # Content or text to type / write
    keys: Optional[List[str]] = None         # Key combo e.g. ["ctrl", "c"]
    key: Optional[str] = None                # Single key e.g. "enter"
    direction: Optional[str] = None          # "up", "down", "left", "right"
    amount: Optional[int] = None             # Scroll units or count
    target: Optional[str] = None             # UI element name or target label
    query: Optional[str] = None              # Search query
    path: Optional[str] = None               # File or folder path
    destination: Optional[str] = None        # Move/copy destination path
    command: Optional[str] = None            # Terminal command to execute
    instruction: Optional[str] = None        # Code instruction or prompt
    scope: Optional[str] = None              # Search scope or folder alias
    line_number: Optional[int] = None        # Target editor line number
    wait_milliseconds: Optional[int] = None  # Wait duration
    # Targeted Semantic Code Patch fields
    target_code: Optional[str] = None        # Exact or fuzzy code snippet to locate and replace
    replacement_code: Optional[str] = None   # Replacement code block
    symbol: Optional[str] = None             # Targeted function, class, or variable name
    patch_action: Optional[str] = "replace"  # "replace", "insert_before", "insert_after", "delete"


class AgentPlan(BaseModel):
    reply: str                               # Spoken and displayed response
    actions: List[AgentAction] = Field(default_factory=list)
    needs_confirmation: bool = False         # Whether any action requires confirmation
    reasoning: Optional[str] = None          # Internal reasoning or explanation
    confidence: float = 1.0                  # Confidence score (0.0 to 1.0)
    intent: Optional[str] = None             # Intent classification (e.g. "conversation", "code_modification", "code_inspection")


class ScreenContext(BaseModel):
    active_app: str = "Unknown"              # Process/app name (e.g. "Code.exe", "chrome.exe")
    active_window_title: str = ""            # Title of the focused window
    window_handle: int = 0                   # Win32 HWND
    process_id: int = 0                      # Process ID
    explorer_path: Optional[str] = None      # Currently open folder in active File Explorer
    vscode_file: Optional[str] = None        # Currently active file in VS Code
    vscode_line: Optional[int] = None        # Cursor line in VS Code
    vscode_workspace: Optional[str] = None   # Open folder in VS Code
    clipboard_text: Optional[str] = None     # Current clipboard text (truncated)
    selected_text: Optional[str] = None      # Highlighted text (if accessible)
    recent_history: Optional[List[Dict[str, Any]]] = None # Multi-turn conversation history for LLM
    # Conversational code context
    focused_code_snippet: Optional[str] = None # Relevant lines around cursor/active function
    last_modified_file: Optional[str] = None   # Most recently edited file
    last_modified_symbol: Optional[str] = None # Most recently edited function/class
    last_edit_summary: Optional[str] = None    # Summary of recent patch


class ConfirmationRequest(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    prompt: str                              # What to ask the user
    actions: List[AgentAction]               # Actions waiting to be executed
    risk_level: str = "medium"               # "low", "medium", "high", "critical"
    diff_text: Optional[str] = None          # Visual diff for code modifications
    target_path: Optional[str] = None        # Targeted file/folder path


class ActionResult(BaseModel):
    action_id: str
    action_type: str
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
