from pathlib import Path
from typing import Optional
from app.core.models import AgentAction
from app.logging.logger import logger


class FriendlyErrorTranslator:
    """
    Translates raw internal Python/OS exceptions into natural, polite,
    and actionable voice responses suitable for speech synthesis.
    """

    @classmethod
    def translate(cls, error: Exception, action: Optional[AgentAction] = None) -> str:
        err_str = str(error).strip()
        act_type = (action.type if action else "").lower()

        # 1. File Not Found Errors
        if isinstance(error, FileNotFoundError) or "file not found" in err_str.lower() or "not found" in err_str.lower():
            target = ""
            if action:
                target = action.path or action.app or action.destination or ""
            target_clean = Path(target).name if target else "that item"

            # Check if user was looking for a known tool/app
            lower_target = target_clean.lower()
            if "explorer" in lower_target:
                return "I couldn't find that file. Did you mean to open File Explorer?"
            elif "post" in lower_target and "sql" in lower_target:
                return "I couldn't find an application named 'post grey sql'. Did you mean PostgreSQL?"
            elif "chrome" in lower_target:
                return "I couldn't find Google Chrome on this PC."
            elif "vscode" in lower_target or "code" in lower_target:
                return "I couldn't find Visual Studio Code on this PC."

            if act_type in ["open_file", "trash_path", "rename_path", "move_path", "copy_path"]:
                return f"I couldn't find the file '{target_clean}' in that location. Please check the name or folder."
            elif act_type in ["open_app", "close_app"]:
                return f"I couldn't find an application called '{target_clean}' installed on this PC."
            elif act_type == "open_folder":
                return f"I couldn't find the folder '{target_clean}'. Would you like me to create it?"
            return f"I couldn't find '{target_clean}' on your PC."

        # 2. Permission Errors
        if isinstance(error, PermissionError) or "access is denied" in err_str.lower() or "permission denied" in err_str.lower():
            return "Windows denied access to that file or folder. Administrator permission may be required."

        # 3. File or Folder Already Exists
        if isinstance(error, FileExistsError) or "already exists" in err_str.lower():
            target = action.path if action else "that item"
            name = Path(target).name if target else "An item"
            return f"An item named '{name}' already exists in that folder."

        # 4. Connection / Network Timeouts
        if isinstance(error, TimeoutError) or "timed out" in err_str.lower() or "connecterror" in err_str.lower():
            return "The request timed out. Please check your internet connection and try again."

        # 5. Generic Safe Voice Fallback
        # Never output long raw stack traces to TTS
        clean_msg = err_str.split("\n")[0]
        if len(clean_msg) > 90:
            clean_msg = clean_msg[:87] + "..."

        logger.debug(f"Translated generic error: '{err_str}'")
        return f"I ran into an issue: {clean_msg}"


friendly_errors = FriendlyErrorTranslator()
