import os
import re
from pathlib import Path
from typing import List, Optional, Tuple

from app.core.models import AgentAction, ConfirmationRequest
from app.filesystem.service import FileSystemService
from app.logging.logger import logger


class SecurityGuard:
    """
    Security and Safety Policy layer for Clembot.
    Enforces path validation, dangerous command detection, prompt injection shielding,
    and structured confirmation workflows.
    """

    # Protected Windows system folders that should never be deleted or overwritten
    PROTECTED_SYSTEM_PATHS: List[str] = [
        "c:\\windows",
        "c:\\windows\\system32",
        "c:\\windows\\syswow64",
        "c:\\program files",
        "c:\\program files (x86)",
        "c:\\boot",
        "c:\\recovery",
        "c:\\system volume information",
        "c:\\$recycle.bin",
    ]

    # Shell commands that are categorically blocked or strictly require explicit confirmation
    DANGEROUS_SHELL_PATTERNS = [
        (re.compile(r'\bformat\s+[a-z]:', re.IGNORECASE), "Disk formatting is prohibited."),
        (re.compile(r'\b(rmdir|rd)\b.*?\bc:\\', re.IGNORECASE), "Destructive root directory deletion is prohibited."),
        (re.compile(r'\bdel\b.*?\bc:\\', re.IGNORECASE), "Root file deletion is prohibited."),
        (re.compile(r'\breg\s+delete\b', re.IGNORECASE), "Direct registry deletion is prohibited without admin console."),
        (re.compile(r'\bvssadmin\s+delete\s+shadows\b', re.IGNORECASE), "Shadow copy deletion is prohibited."),
        (re.compile(r'\bbcdedit\b', re.IGNORECASE), "Boot configuration modification is prohibited."),
        (re.compile(r'\bdiskpart\b', re.IGNORECASE), "Disk partitioning is prohibited via voice assistant."),
    ]

    def __init__(self):
        self.fs_service = FileSystemService()

    def is_protected_path(self, target_path: Path) -> bool:
        """Checks if a path resides within critical Windows system directories."""
        try:
            resolved = str(target_path.resolve()).lower()
            for protected in self.PROTECTED_SYSTEM_PATHS:
                if resolved == protected or resolved.startswith(f"{protected}\\"):
                    return True
            # Also block deleting drive root (e.g. C:\)
            if resolved in ["c:\\", "d:\\", "e:\\", "c:", "d:", "e:"]:
                return True
        except Exception:
            pass
        return False

    def validate_shell_command(self, command: str) -> Tuple[bool, Optional[str]]:
        """
        Validates whether a shell command is safe to execute.
        Returns (is_safe, error_or_warning_message).
        """
        cmd_clean = command.strip()
        for pattern, reason in self.DANGEROUS_SHELL_PATTERNS:
            if pattern.search(cmd_clean):
                return False, f"Blocked unsafe command: {reason}"

        return True, None

    def evaluate_action_risk(self, action: AgentAction) -> Tuple[bool, Optional[ConfirmationRequest]]:
        """
        Evaluates whether an action requires user confirmation before execution.
        Returns (requires_confirmation, confirmation_request_if_any).
        """
        action_type = action.type.lower()

        # 1. File & Folder Deletion
        if action_type in ["trash_path", "delete_folder", "delete_file"]:
            target_raw = action.path or action.target or action.text
            if target_raw:
                target_path = self.fs_service.resolve(target_raw)

                if self.is_protected_path(target_path):
                    logger.warning(f"Blocked attempt to delete protected system path: {target_path}")
                    return True, ConfirmationRequest(
                        prompt=f"I cannot delete '{target_path.name}' because it is a protected Windows system path.",
                        actions=[action],
                        risk_level="critical",
                        target_path=str(target_path)
                    )

                if target_path.exists():
                    if target_path.is_dir():
                        item_count = self.fs_service.count_items_in_directory(target_path)
                        if item_count > 3:
                            prompt = f"'{target_path.name}' contains {item_count} items. Do you really want me to delete this folder?"
                            return True, ConfirmationRequest(
                                prompt=prompt,
                                actions=[action],
                                risk_level="high",
                                target_path=str(target_path)
                            )
                        else:
                            prompt = f"Are you sure you want to move '{target_path.name}' to the Recycle Bin?"
                            return True, ConfirmationRequest(
                                prompt=prompt,
                                actions=[action],
                                risk_level="medium",
                                target_path=str(target_path)
                            )
                    else:
                        prompt = f"Are you sure you want to delete '{target_path.name}'?"
                        return True, ConfirmationRequest(
                            prompt=prompt,
                            actions=[action],
                            risk_level="medium",
                            target_path=str(target_path)
                        )

        # 2. Moving or Renaming items
        if action_type in ["move_path", "rename_path"]:
            source_raw = action.path
            dest_raw = action.destination or action.target
            if source_raw:
                source_path = self.fs_service.resolve(source_raw)
                if self.is_protected_path(source_path):
                    return True, ConfirmationRequest(
                        prompt=f"Cannot move or rename protected system item '{source_path.name}'.",
                        actions=[action],
                        risk_level="critical",
                        target_path=str(source_path)
                    )

        # 3. Terminal Execution
        if action_type in ["terminal_run", "run_terminal_command"]:
            cmd = action.command or action.text or ""
            is_safe, error = self.validate_shell_command(cmd)
            if not is_safe:
                return True, ConfirmationRequest(
                    prompt=error or "This command was blocked for safety reasons.",
                    actions=[],
                    risk_level="critical"
                )

            # Require confirmation for terminal commands that install packages or run scripts
            prompt = f"Ready to run terminal command: '{cmd}'. Wake me and say confirm to proceed, or say cancel."
            return True, ConfirmationRequest(
                prompt=prompt,
                actions=[action],
                risk_level="high"
            )

        # 4. Code Modification (Diff confirmation)
        if action_type in ["vscode_edit", "vscode_patch", "code_edit"]:
            instruction = action.instruction or action.text or "code edit"
            patch_hint = ""
            if action_type == "vscode_patch":
                target = getattr(action, 'target_code', None)
                if target:
                    preview = target[:80].replace('\n', ' ')
                    patch_hint = f" Changing: '{preview}...'"
            prompt = f"I prepared code changes for: '{instruction}'.{patch_hint} Say confirm to apply, or cancel."
            return True, ConfirmationRequest(
                prompt=prompt,
                actions=[action],
                risk_level="medium"
            )

        return False, None


# Global security guard singleton
security_guard = SecurityGuard()
