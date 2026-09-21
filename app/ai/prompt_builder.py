import json
import re
from typing import Any, Dict, List, Optional, Set
from pydantic import ValidationError

from app.config.settings import settings
from app.core.models import AgentAction, AgentPlan, ScreenContext
from app.logging.logger import logger


class AIPromptBuilder:
    """
    Constructs structured system instructions and context-rich prompts for AI models,
    and provides strict Pydantic validation with schema enforcement.
    """

    VALID_ACTION_TYPES: Set[str] = {
        # File System
        "open_folder", "create_folder", "create_file", "rename_path",
        "move_path", "copy_path", "trash_path", "list_directory", "find_file",
        # Windows & Apps
        "open_app", "close_app", "window_minimize", "window_maximize",
        "window_restore", "window_close", "window_snap_left", "window_snap_right",
        "window_center", "show_desktop",
        # Web & Browser
        "web_search", "open_url", "browser_new_tab", "browser_close_tab",
        "browser_next_tab", "browser_prev_tab", "browser_reload",
        # VS Code & Code Editing
        "vscode_jump_line", "vscode_open_file", "vscode_edit", "vscode_run_code",
        "vscode_undo", "vscode_read_line",
        # System & Clipboard
        "screenshot", "volume_up", "volume_down", "volume_mute",
        "copy", "paste", "clear_clipboard", "select_all", "undo", "redo", "save",
        # Conversational Question Answering
        "answer_question"
    }

    SYSTEM_INSTRUCTION = """You are Clembot, an intelligent, helpful voice assistant and conversational companion on Windows 10/11.

CORE RESPONSIBILITIES:
1. DESKTOP AUTOMATION: When the user asks to control Windows (open apps, manipulate files/folders, adjust volume, take screenshots, snap windows, edit code in VS Code), return the exact actions in the "actions" array and a concise spoken confirmation in "reply".
2. CONVERSATIONAL SPEECH & QUESTIONS: When the user asks general questions, explanations, distance, weather, recipes, code advice, jokes, chit-chat, or speaks in Hindi/Hinglish, provide a natural, clear, and informative spoken answer in the "reply" field. You may set "actions" to an empty list [] or use the "answer_question" action.
3. MULTI-STEP PLANS: If the user asks for multiple steps (e.g. "Create a folder called AI on Desktop and open it"), output each action in sequence in the "actions" list.

VOICE & TTS OUTPUT RULES:
- The "reply" string is spoken aloud to the user using Windows Text-to-Speech (TTS).
- Keep replies natural, concise, and direct (1 to 3 spoken sentences).
- NEVER use markdown formatting (no asterisks, bullet points, numbered lists, hashtags, bolding, emojis, or code blocks) inside the "reply" text. Markdown symbols sound unnatural when spoken.

ALLOWED ACTION TYPES:
- open_folder (path)
- create_folder (path)
- create_file (path, text)
- rename_path (path, destination)
- move_path (path, destination)
- copy_path (path, destination)
- trash_path (path)
- list_directory (path)
- find_file (query, scope)
- open_app (app)
- close_app (app)
- window_minimize, window_maximize, window_restore, window_close, window_snap_left, window_snap_right, window_center, show_desktop
- web_search (query, scope)
- open_url (url)
- browser_new_tab, browser_close_tab, browser_next_tab, browser_prev_tab, browser_reload
- vscode_jump_line (line_number)
- vscode_open_file (path)
- vscode_read_line (line_number)  — read and speak the content of a line
- vscode_edit (text)  — code editing; set "text" to one of these structured tokens:
    REPLACE_IN_LINE:<line>:<old>::<new>   (replace first occurrence of <old> with <new> on line N)
    REPLACE_LINE:<line>::<new_text>       (overwrite entire line N)
    DELETE_LINE:<line>                    (delete line N)
    DELETE_LINES:<start>:<end>            (delete lines start to end inclusive)
    INSERT_AFTER:<line>::<text>           (insert new line after line N)
    INSERT_BEFORE:<line>::<text>          (insert new line before line N)
    COMMENT_LINE:<line>                   (comment out line N)
    UNCOMMENT_LINE:<line>                 (uncomment line N)
    RENAME_FUNC:<old>:<new>              (rename a function across the whole file)
    ADD_TRY_EXCEPT:<line>               (wrap line N in try/except)
    Or a plain English instruction for complex edits (AI will apply it)
- vscode_run_code, vscode_undo
- screenshot, volume_up, volume_down, volume_mute
- copy, paste, clear_clipboard, select_all, undo, redo, save
- answer_question (query)

SCHEMA:
Return a valid JSON object matching this exact structure:
{
  "reply": "Spoken verbal response to user",
  "actions": [
    {
      "type": "string (one of the allowed action types above)",
      "path": "optional string",
      "destination": "optional string",
      "app": "optional string",
      "url": "optional string",
      "query": "optional string",
      "text": "optional string",
      "instruction": "optional string",
      "line_number": null,
      "scope": "optional string"
    }
  ]
}
Output valid JSON only. Do not include markdown code block backticks outside the JSON.
"""

    @classmethod
    def build_system_instruction(cls) -> str:
        return cls.SYSTEM_INSTRUCTION

    @classmethod
    def build_user_prompt(cls, command: str, context: ScreenContext) -> str:
        """Assembles a context-rich user prompt including live desktop context and history."""
        sections = []

        # 1. Recent conversation history
        if context.recent_history:
            recent_turns = [
                f"{t.get('role', 'user').capitalize()}: {t.get('content', '')}"
                for t in context.recent_history[-6:]
            ]
            sections.append("Recent Conversation:\n" + "\n".join(recent_turns))

        # 2. Real-time Desktop Context
        desktop_info = [
            f"- Active Window: {context.active_window_title or 'Unknown'} ({context.active_app or 'Unknown'})",
            f"- Focused File Explorer Path: {context.explorer_path or 'None'}",
            f"- Active VS Code File: {context.vscode_file or 'None'}",
        ]
        sections.append("Windows Desktop State:\n" + "\n".join(desktop_info))

        # 3. User spoken input
        sections.append(f"User Spoken Command: \"{command}\"")

        return "\n\n".join(sections)

    @classmethod
    def build_retry_prompt(cls, original_prompt: str, error_msg: str, invalid_output: str) -> str:
        """Constructs a targeted prompt asking the model to fix its invalid JSON output."""
        return (
            f"{original_prompt}\n\n"
            f"[SYSTEM FEEDBACK]: Your previous response could not be parsed: {error_msg}\n"
            f"Previous output was: {invalid_output[:400]}\n"
            f"Please respond with strictly valid JSON following the schema without markdown."
        )

    @classmethod
    def parse_and_validate(cls, raw_text: str) -> AgentPlan:
        """
        Parses and validates the raw LLM output into an AgentPlan.
        Validates against Pydantic schema and enforces allowed action types.
        Raises ValueError on parse failure.
        """
        cleaned = raw_text.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r'^```(?:json)?\s*', '', cleaned)
            cleaned = re.sub(r'\s*```$', '', cleaned).strip()

        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError as e:
            # If the output is pure conversational text, wrap it cleanly
            if "{" not in cleaned and "}" not in cleaned and len(cleaned) > 0:
                return AgentPlan(reply=cleaned, actions=[])
            raise ValueError(f"Invalid JSON syntax from model: {e}")

        if not isinstance(data, dict):
            raise ValueError("Root response must be a JSON object.")

        reply = data.get("reply", "")
        raw_actions = data.get("actions", [])

        if not isinstance(raw_actions, list):
            raise ValueError("'actions' field must be an array.")

        validated_actions: List[AgentAction] = []
        for i, a in enumerate(raw_actions):
            if not isinstance(a, dict):
                raise ValueError(f"Action at index {i} must be a dictionary.")

            act_type = str(a.get("type", "")).lower().strip()
            if not settings.allow_unknown_actions and act_type not in cls.VALID_ACTION_TYPES:
                logger.warning(f"Rejected unknown action type from LLM: '{act_type}'")
                continue

            try:
                action_obj = AgentAction(**a)
                validated_actions.append(action_obj)
            except ValidationError as ve:
                raise ValueError(f"Action validation failed at index {i}: {ve}")

        return AgentPlan(reply=reply, actions=validated_actions)


prompt_builder = AIPromptBuilder()
