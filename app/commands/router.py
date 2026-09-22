from pathlib import Path
from typing import Optional
from app.automation.input_adapter import WindowsInputAdapter
from app.browser.controller import BrowserController
from app.clipboard.manager import WindowsClipboardManager
from app.commands.friendly_errors import friendly_errors
from app.core.models import ActionResult, AgentAction
from app.editor.code_intelligence import CodeIntelligenceEngine
from app.editor.vscode_adapter import VSCodeAdapter
from app.filesystem.paths import WindowsPathResolver
from app.filesystem.search import FileSearchService
from app.filesystem.service import FileSystemService
from app.logging.logger import logger
from app.windows.apps import WindowsAppCatalog
from app.windows.system import WindowsSystemControls
from app.windows.window_manager import WindowsWindowManager


class ActionRouter:
    """
    Executes AgentAction objects by routing them to the appropriate Windows subsystem.
    Returns an ActionResult detailing outcome and response.
    """

    def __init__(self):
        self.fs = FileSystemService()
        self.search = FileSearchService()
        self.apps = WindowsAppCatalog()
        self.windows = WindowsWindowManager()
        self.browser = BrowserController()
        self.clipboard = WindowsClipboardManager()
        self.input_adapter = WindowsInputAdapter()
        self.vscode = VSCodeAdapter()
        self.code_engine = CodeIntelligenceEngine()

    def execute(self, action: AgentAction, context_base: Optional[Path] = None) -> ActionResult:
        act_type = action.type.lower()
        logger.info(f"Routing action: {act_type} (params: {action.model_dump(exclude_none=True)})")

        try:
            # 1. Filesystem actions
            if act_type == "open_folder":
                msg = self.fs.open_folder(action.path or "Downloads")
                return ActionResult(action_id=action.id, action_type=act_type, success=True, message=msg)

            elif act_type == "open_file":
                target_str = (action.path or "").strip()
                lower_target = target_str.lower()
                if lower_target in ["explorer", "file explorer", "taskmgr", "task manager", "settings", "control"]:
                    msg = self.apps.open_or_activate(target_str)
                    return ActionResult(action_id=action.id, action_type="open_app", success=True, message=msg)

                try:
                    msg = self.fs.open_file(action.path)
                    return ActionResult(action_id=action.id, action_type=act_type, success=True, message=msg)
                except FileNotFoundError:
                    # Check if target is an installed application before erroring
                    try:
                        msg = self.apps.open_or_activate(target_str)
                        return ActionResult(action_id=action.id, action_type="open_app", success=True, message=msg)
                    except Exception:
                        raise

            elif act_type == "create_folder":
                msg = self.fs.create_folder(action.path, context_base)
                return ActionResult(action_id=action.id, action_type=act_type, success=True, message=msg)

            elif act_type == "create_file":
                msg = self.fs.create_file(action.path, action.text or "", context_base)
                return ActionResult(action_id=action.id, action_type=act_type, success=True, message=msg)

            elif act_type == "rename_path":
                msg = self.fs.rename_item(action.path, action.destination)
                return ActionResult(action_id=action.id, action_type=act_type, success=True, message=msg)

            elif act_type == "move_path":
                msg = self.fs.move_item(action.path, action.destination)
                return ActionResult(action_id=action.id, action_type=act_type, success=True, message=msg)

            elif act_type == "copy_path":
                dest = action.destination or "Desktop"
                msg = self.fs.copy_item(action.path, dest)
                return ActionResult(action_id=action.id, action_type=act_type, success=True, message=msg)

            elif act_type == "trash_path":
                msg = self.fs.delete_item(action.path)
                return ActionResult(action_id=action.id, action_type=act_type, success=True, message=msg)

            elif act_type == "list_directory":
                msg, data = self.fs.list_directory(action.path or "Downloads")
                return ActionResult(action_id=action.id, action_type=act_type, success=True, message=msg, data=data)

            elif act_type == "find_file":
                found = self.search.find_first(action.query, scope=action.scope)
                if found:
                    self.fs.open_file(found)
                    return ActionResult(action_id=action.id, action_type=act_type, success=True, message=f"Found and opening '{found.name}'.")
                return ActionResult(action_id=action.id, action_type=act_type, success=False, message=f"I couldn't find '{action.query}' in your files.")

            # 2. Application & Window Control
            elif act_type == "open_app":
                target = (action.app or "").strip()
                # 1. Try launching or activating the application
                try:
                    msg = self.apps.open_or_activate(target)
                    return ActionResult(action_id=action.id, action_type=act_type, success=True, message=msg)
                except Exception as app_err:
                    logger.debug(f"App catalog could not launch '{target}': {app_err}")

                # 2. Check if target is an existing folder or drive
                try:
                    resolved_path = WindowsPathResolver.resolve(target, context_base=context_base)
                    if resolved_path and resolved_path.exists():
                        if resolved_path.is_dir():
                            msg = self.fs.open_folder(resolved_path)
                        else:
                            msg = self.fs.open_file(resolved_path)
                        return ActionResult(action_id=action.id, action_type=act_type, success=True, message=msg)
                except Exception as path_err:
                    logger.debug(f"Path resolver could not open '{target}': {path_err}")

                # 3. Search for matching file or folder in user directories
                found = self.search.find_first(target)
                if found and found.exists():
                    if found.is_dir():
                        msg = self.fs.open_folder(found)
                    else:
                        msg = self.fs.open_file(found)
                    return ActionResult(action_id=action.id, action_type=act_type, success=True, message=f"Found and opened '{found.name}'.")

                # 4. Check if target is a web destination
                dest_msg = self.browser.open_web_destination(target)
                if dest_msg:
                    return ActionResult(action_id=action.id, action_type=act_type, success=True, message=dest_msg)

                # 5. Fallback: Search the web
                search_msg = self.browser.search_web(target)
                return ActionResult(action_id=action.id, action_type="web_search", success=True, message=f"Couldn't find '{target}' locally. {search_msg}")

            elif act_type == "close_app":
                msg = self.apps.close_app(action.app)
                return ActionResult(action_id=action.id, action_type=act_type, success=True, message=msg)

            elif act_type == "window_minimize":
                msg = self.windows.minimize_current()
                return ActionResult(action_id=action.id, action_type=act_type, success=True, message=msg)

            elif act_type == "window_maximize":
                msg = self.windows.maximize_current()
                return ActionResult(action_id=action.id, action_type=act_type, success=True, message=msg)

            elif act_type == "window_restore":
                msg = self.windows.restore_current()
                return ActionResult(action_id=action.id, action_type=act_type, success=True, message=msg)

            elif act_type == "window_close":
                msg = self.windows.close_current()
                return ActionResult(action_id=action.id, action_type=act_type, success=True, message=msg)

            elif act_type == "window_snap_left":
                msg = self.windows.snap_left()
                return ActionResult(action_id=action.id, action_type=act_type, success=True, message=msg)

            elif act_type == "window_snap_right":
                msg = self.windows.snap_right()
                return ActionResult(action_id=action.id, action_type=act_type, success=True, message=msg)

            elif act_type == "window_center":
                msg = self.windows.center_window()
                return ActionResult(action_id=action.id, action_type=act_type, success=True, message=msg)

            elif act_type == "show_desktop":
                msg = self.windows.show_desktop()
                return ActionResult(action_id=action.id, action_type=act_type, success=True, message=msg)

            # 3. Browser & Web
            elif act_type == "web_search":
                msg = self.browser.search_web(action.query, engine=action.scope)
                return ActionResult(action_id=action.id, action_type=act_type, success=True, message=msg)

            elif act_type == "open_url":
                msg = self.browser.open_url(action.url)
                return ActionResult(action_id=action.id, action_type=act_type, success=True, message=msg)

            elif act_type == "browser_new_tab":
                msg = self.browser.new_tab()
                return ActionResult(action_id=action.id, action_type=act_type, success=True, message=msg)

            elif act_type == "browser_close_tab":
                msg = self.browser.close_tab()
                return ActionResult(action_id=action.id, action_type=act_type, success=True, message=msg)

            elif act_type == "browser_next_tab":
                msg = self.browser.next_tab()
                return ActionResult(action_id=action.id, action_type=act_type, success=True, message=msg)

            elif act_type == "browser_prev_tab":
                msg = self.browser.previous_tab()
                return ActionResult(action_id=action.id, action_type=act_type, success=True, message=msg)

            elif act_type == "browser_reload":
                msg = self.browser.reload()
                return ActionResult(action_id=action.id, action_type=act_type, success=True, message=msg)

            # 4. System & Clipboard
            elif act_type == "screenshot":
                path, msg = WindowsSystemControls.capture_screenshot()
                return ActionResult(action_id=action.id, action_type=act_type, success=True, message=msg, data={"path": str(path)})

            elif act_type == "volume_up":
                msg = WindowsSystemControls.volume_up()
                return ActionResult(action_id=action.id, action_type=act_type, success=True, message=msg)

            elif act_type == "volume_down":
                msg = WindowsSystemControls.volume_down()
                return ActionResult(action_id=action.id, action_type=act_type, success=True, message=msg)

            elif act_type == "volume_mute":
                msg = WindowsSystemControls.volume_mute_toggle()
                return ActionResult(action_id=action.id, action_type=act_type, success=True, message=msg)

            elif act_type == "copy":
                self.input_adapter.copy()
                return ActionResult(action_id=action.id, action_type=act_type, success=True, message="Copied.")

            elif act_type == "paste":
                self.input_adapter.paste()
                return ActionResult(action_id=action.id, action_type=act_type, success=True, message="Pasted.")

            elif act_type == "clear_clipboard":
                msg = self.clipboard.clear()
                return ActionResult(action_id=action.id, action_type=act_type, success=True, message=msg)

            elif act_type == "select_all":
                self.input_adapter.select_all()
                return ActionResult(action_id=action.id, action_type=act_type, success=True, message="Selected all.")

            elif act_type == "undo":
                self.input_adapter.undo()
                return ActionResult(action_id=action.id, action_type=act_type, success=True, message="Undone.")

            elif act_type == "redo":
                self.input_adapter.redo()
                return ActionResult(action_id=action.id, action_type=act_type, success=True, message="Redone.")

            elif act_type == "save":
                self.input_adapter.save()
                return ActionResult(action_id=action.id, action_type=act_type, success=True, message="Saved.")

            # 5. VS Code & Code Editing
            elif act_type == "vscode_jump_line":
                line_num = action.line_number or 1
                success = self.vscode.jump_to_line(line_num)
                return ActionResult(action_id=action.id, action_type=act_type, success=success, message=f"Jumped to line {line_num}.")

            elif act_type == "vscode_open_file":
                target_p = WindowsPathResolver.resolve(action.path)
                success = self.vscode.open_file(target_p)
                return ActionResult(action_id=action.id, action_type=act_type, success=success, message=f"Opened '{target_p.name}' in VS Code.")

            elif act_type == "vscode_run_code":
                success = self.vscode.run_code()
                return ActionResult(action_id=action.id, action_type=act_type, success=success, message="Started execution.")

            elif act_type == "vscode_undo":
                success = self.vscode.undo()
                return ActionResult(action_id=action.id, action_type=act_type, success=success, message="Reverted code edit.")

            elif act_type == "vscode_read_line":
                line_num = action.line_number or 1
                content = self.vscode.read_document()
                if content:
                    lines = content.splitlines()
                    idx = line_num - 1
                    if 0 <= idx < len(lines):
                        line_text = lines[idx].strip()
                        msg = f"Line {line_num} says: {line_text}" if line_text else f"Line {line_num} is empty."
                    else:
                        msg = f"Line {line_num} does not exist in this file."
                else:
                    msg = "Could not read the file. Make sure a file is open in VS Code."
                return ActionResult(action_id=action.id, action_type=act_type, success=True, message=msg)

            elif act_type == "vscode_edit":
                # Resolve active file
                active_file = self.vscode.get_active_file()
                if not active_file or not active_file.is_file():
                    active_file = context_base if context_base and context_base.is_file() else None
                if not active_file:
                    return ActionResult(action_id=action.id, action_type=act_type, success=False,
                                        message="No active code file detected. Please open a file in VS Code first.")

                token = (action.text or action.instruction or "").strip()

                # ------ A. REPLACE_IN_LINE:{line}:{old}::{new} ------
                if token.startswith("REPLACE_IN_LINE:"):
                    # format: REPLACE_IN_LINE:<line>:<old>::<new>
                    rest = token[len("REPLACE_IN_LINE:"):]
                    parts = rest.split("::", 1)
                    if len(parts) == 2:
                        header, new_val = parts
                        header_parts = header.split(":", 1)
                        if len(header_parts) == 2:
                            ln, old_val = int(header_parts[0]), header_parts[1]
                            result_msg = self._file_replace_in_line(active_file, ln, old_val, new_val)
                            self.vscode.open_file(active_file)
                            return ActionResult(action_id=action.id, action_type=act_type, success=True, message=result_msg)
                    return ActionResult(action_id=action.id, action_type=act_type, success=False,
                                        message="Could not parse the replace instruction.")

                # ------ B. REPLACE_LINE:{line}::{new_text} ------
                elif token.startswith("REPLACE_LINE:"):
                    rest = token[len("REPLACE_LINE:"):]
                    parts = rest.split("::", 1)
                    if len(parts) == 2:
                        ln, new_text = int(parts[0]), parts[1]
                        ok = self.vscode.apply_edit(active_file, ln, ln, new_text)
                        self.vscode.open_file(active_file)
                        msg = f"Line {ln} replaced." if ok else f"Could not replace line {ln}."
                        return ActionResult(action_id=action.id, action_type=act_type, success=ok, message=msg)

                # ------ C. DELETE_LINE:{line} ------
                elif token.startswith("DELETE_LINE:") and not token.startswith("DELETE_LINES:"):
                    ln = int(token[len("DELETE_LINE:"):])
                    ok = self._file_delete_lines(active_file, ln, ln)
                    self.vscode.open_file(active_file)
                    return ActionResult(action_id=action.id, action_type=act_type, success=ok,
                                        message=f"Line {ln} deleted." if ok else f"Could not delete line {ln}.")

                # ------ D. DELETE_LINES:{start}:{end} ------
                elif token.startswith("DELETE_LINES:"):
                    parts = token[len("DELETE_LINES:"):].split(":")
                    if len(parts) == 2:
                        s, e = int(parts[0]), int(parts[1])
                        ok = self._file_delete_lines(active_file, s, e)
                        self.vscode.open_file(active_file)
                        return ActionResult(action_id=action.id, action_type=act_type, success=ok,
                                            message=f"Lines {s} to {e} deleted." if ok else "Could not delete lines.")

                # ------ E. INSERT_AFTER:{line}::{text} ------
                elif token.startswith("INSERT_AFTER:"):
                    rest = token[len("INSERT_AFTER:"):]
                    parts = rest.split("::", 1)
                    if len(parts) == 2:
                        ln, new_text = int(parts[0]), parts[1]
                        ok = self._file_insert_line(active_file, ln, new_text, after=True)
                        self.vscode.open_file(active_file)
                        return ActionResult(action_id=action.id, action_type=act_type, success=ok,
                                            message=f"Inserted after line {ln}." if ok else "Insert failed.")

                # ------ F. INSERT_BEFORE:{line}::{text} ------
                elif token.startswith("INSERT_BEFORE:"):
                    rest = token[len("INSERT_BEFORE:"):]
                    parts = rest.split("::", 1)
                    if len(parts) == 2:
                        ln, new_text = int(parts[0]), parts[1]
                        ok = self._file_insert_line(active_file, ln, new_text, after=False)
                        self.vscode.open_file(active_file)
                        return ActionResult(action_id=action.id, action_type=act_type, success=ok,
                                            message=f"Inserted before line {ln}." if ok else "Insert failed.")

                # ------ G. COMMENT_LINE:{line} ------
                elif token.startswith("COMMENT_LINE:"):
                    ln = int(token[len("COMMENT_LINE:"):])
                    ok = self._file_toggle_comment(active_file, ln, add_comment=True)
                    self.vscode.open_file(active_file)
                    return ActionResult(action_id=action.id, action_type=act_type, success=ok,
                                        message=f"Line {ln} commented out." if ok else "Could not comment line.")

                # ------ H. UNCOMMENT_LINE:{line} ------
                elif token.startswith("UNCOMMENT_LINE:"):
                    ln = int(token[len("UNCOMMENT_LINE:"):])
                    ok = self._file_toggle_comment(active_file, ln, add_comment=False)
                    self.vscode.open_file(active_file)
                    return ActionResult(action_id=action.id, action_type=act_type, success=ok,
                                        message=f"Line {ln} uncommented." if ok else "Could not uncomment line.")

                # ------ I. RENAME_FUNC:{old}:{new} ------
                elif token.startswith("RENAME_FUNC:"):
                    parts = token.split(":")
                    if len(parts) >= 3:
                        proposal = self.code_engine.propose_function_rename(active_file, parts[1], parts[2])
                        if proposal:
                            self.code_engine.apply_proposal(proposal)
                            self.vscode.open_file(active_file)
                            return ActionResult(action_id=action.id, action_type=act_type, success=True,
                                                message=proposal.explanation)
                    return ActionResult(action_id=action.id, action_type=act_type, success=False,
                                        message="Could not parse the rename instruction.")

                # ------ J. ADD_TRY_EXCEPT:{line} ------
                elif token.startswith("ADD_TRY_EXCEPT"):
                    parts = token.split(":")
                    ln = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else (action.line_number or 1)
                    proposal = self.code_engine.propose_exception_handling_at_line(active_file, ln)
                    if proposal:
                        self.code_engine.apply_proposal(proposal)
                        self.vscode.open_file(active_file)
                        return ActionResult(action_id=action.id, action_type=act_type, success=True,
                                            message=proposal.explanation)
                    return ActionResult(action_id=action.id, action_type=act_type, success=False,
                                        message="Could not generate the error-handling block.")

                # ------ K. Free-text instruction → targeted patch via code_patch_engine ------
                elif token:
                    from app.editor.code_patch_engine import code_patch_engine, TargetedPatch
                    current_code = self.vscode.read_document(active_file)
                    if not current_code:
                        return ActionResult(action_id=action.id, action_type=act_type, success=False,
                                            message="Could not read the active file.")
                    # Build a vscode_patch action from the free-text instruction via AI
                    from app.ai.factory import AIProviderFactory
                    from app.core.models import ScreenContext
                    import re as _re
                    lines = current_code.splitlines()
                    snippet = "\n".join(f"{i+1}: {l}" for i, l in enumerate(lines[:100]))
                    mini_prompt = (
                        f"You are a code editor. Return a vscode_patch JSON action only.\n"
                        f"Instruction: {token}\n"
                        f"File: {active_file.name}\n"
                        f"Content (first 100 lines):\n{snippet}\n\n"
                        f"Return JSON: {{\"target_code\": \"exact snippet\", \"replacement_code\": \"new snippet\", "
                        f"\"patch_action\": \"replace\", \"explanation\": \"what changed\"}}"
                    )
                    provider = AIProviderFactory.get_provider()
                    ctx = ScreenContext()
                    ctx.vscode_file = str(active_file)
                    mini_plan = provider.plan(mini_prompt, ctx)
                    import json as _json
                    raw = mini_plan.reply.strip()
                    raw = _re.sub(r'^```[^\n]*\n?', '', raw)
                    raw = _re.sub(r'\n?```$', '', raw).strip()
                    patch_data = {}
                    try:
                        patch_data = _json.loads(raw)
                    except Exception:
                        # Fall back: if AI returns whole file, wrap in patch
                        if len(raw) > 20 and not raw.startswith("{"):
                            patch_data = {
                                "target_code": lines[0] if lines else "",
                                "replacement_code": raw,
                                "patch_action": "replace",
                                "explanation": f"Applied: {token}",
                            }

                    if patch_data.get("target_code") and patch_data.get("replacement_code"):
                        tp = TargetedPatch(
                            file_path=active_file,
                            target_code=patch_data["target_code"],
                            replacement_code=patch_data["replacement_code"],
                            explanation=patch_data.get("explanation", f"Applied: {token}"),
                            patch_action=patch_data.get("patch_action", "replace"),
                        )
                        success, msg, diff = code_patch_engine.apply_patch(tp)
                        if success:
                            self.vscode.open_file(active_file)
                        return ActionResult(action_id=action.id, action_type=act_type, success=success, message=msg)
                    return ActionResult(action_id=action.id, action_type=act_type, success=False,
                                        message="Could not determine what to change. Try being more specific.")

                return ActionResult(action_id=action.id, action_type=act_type, success=False,
                                    message="No edit instruction provided.")

            # ------ vscode_patch: targeted semantic patch (preferred code edit path) ------
            elif act_type == "vscode_patch":
                from app.editor.code_patch_engine import code_patch_engine, TargetedPatch
                from pathlib import Path

                target_file: Optional[Path] = None
                if action.path:
                    target_file = WindowsPathResolver.resolve(action.path)
                else:
                    target_file = self.vscode.get_active_file()
                    if not target_file or not target_file.is_file():
                        target_file = context_base if context_base and context_base.is_file() else None

                if not target_file or not target_file.is_file():
                    return ActionResult(action_id=action.id, action_type=act_type, success=False,
                                        message="No active file found. Please open a file in VS Code first.")

                target_code = getattr(action, 'target_code', None) or ""
                replacement_code = getattr(action, 'replacement_code', None) or ""
                if not target_code and not replacement_code:
                    return ActionResult(action_id=action.id, action_type=act_type, success=False,
                                        message="Patch requires target_code and replacement_code.")

                tp = TargetedPatch(
                    file_path=target_file,
                    target_code=target_code,
                    replacement_code=replacement_code,
                    explanation=getattr(action, 'instruction', None) or f"Patched {target_file.name}",
                    line_hint=action.line_number,
                    symbol_name=getattr(action, 'symbol', None),
                    patch_action=getattr(action, 'patch_action', 'replace') or 'replace',
                )
                success, msg, diff = code_patch_engine.apply_patch(tp)
                if success:
                    self.vscode.open_file(target_file)
                return ActionResult(action_id=action.id, action_type=act_type, success=success, message=msg)

            # ------ vscode_inspect: explain active file or selection ------
            elif act_type == "vscode_inspect":
                active_file = self.vscode.get_active_file()
                if not active_file or not active_file.is_file():
                    return ActionResult(action_id=action.id, action_type=act_type, success=False,
                                        message="No active file found in VS Code.")
                ctx_info = self.code_engine.inspect_active_context(active_file, line_hint=None)
                if ctx_info:
                    msg = f"In {active_file.name}: {ctx_info}"
                else:
                    msg = f"Opened {active_file.name}. Unable to extract context automatically."
                return ActionResult(action_id=action.id, action_type=act_type, success=True, message=msg)

            # ------ vscode_outline: speak file structure ------
            elif act_type == "vscode_outline":
                active_file = self.vscode.get_active_file()
                if not active_file or not active_file.is_file():
                    return ActionResult(action_id=action.id, action_type=act_type, success=False,
                                        message="No active file found in VS Code.")
                outline = self.code_engine.extract_file_outline(active_file)
                if outline:
                    parts = [f"{s['kind']} {s['name']} at line {s['line']}" for s in outline[:8]]
                    msg = f"{active_file.name} contains: " + ", ".join(parts)
                else:
                    msg = f"Could not extract outline from {active_file.name}."
                return ActionResult(action_id=action.id, action_type=act_type, success=True, message=msg)

            # ------ vscode_find_symbols: search workspace for a symbol ------
            elif act_type == "vscode_find_symbols":
                query = action.query or getattr(action, 'text', None) or ""
                if not query:
                    return ActionResult(action_id=action.id, action_type=act_type, success=False,
                                        message="Please specify what symbol or function to find.")
                scope_dir = None
                if action.scope:
                    from pathlib import Path
                    scope_dir = Path(action.scope) if Path(action.scope).is_dir() else None
                if not scope_dir and context_base:
                    scope_dir = context_base if context_base.is_dir() else context_base.parent
                if not scope_dir:
                    return ActionResult(action_id=action.id, action_type=act_type, success=False,
                                        message="No workspace directory found. Open a folder in VS Code first.")
                results = self.code_engine.find_symbols_in_workspace(query, scope_dir)
                if results:
                    parts = [f"{r['symbol']} in {r['file']} at line {r['line']}" for r in results[:5]]
                    msg = "Found: " + "; ".join(parts)
                else:
                    msg = f"No results for '{query}' in the workspace."
                return ActionResult(action_id=action.id, action_type=act_type, success=True, message=msg)

            elif act_type == "answer_question":
                reply_text = action.text or action.query or ""
                return ActionResult(action_id=action.id, action_type=act_type, success=True, message=reply_text)

            else:
                return ActionResult(action_id=action.id, action_type=act_type, success=False, message=f"Unknown action type: {act_type}")

        except Exception as e:
            logger.error(f"Action execution error ({act_type}): {e}")
            spoken_msg = friendly_errors.translate(e, action)
            return ActionResult(action_id=action.id, action_type=act_type, success=False, message=spoken_msg, error=str(e))

    # ------------------------------------------------------------------
    # Private file-manipulation helpers (no IPC required — operate on disk)
    # All create a .bak backup before writing.
    # ------------------------------------------------------------------

    @staticmethod
    def _read_lines(path: Path):
        """
        Read a file and return (lines_with_endings, detected_eol).
        Always reads as bytes first to avoid Python's newline translation,
        then decodes as UTF-8 (with cp1252 fallback).
        splitlines(keepends=True) correctly handles \r\n, \n, and \r.
        """
        raw = path.read_bytes()
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            text = raw.decode("cp1252", errors="replace")
        # Detect the dominant EOL style in this file
        crlf_count = text.count("\r\n")
        lf_count   = text.count("\n") - crlf_count
        eol = "\r\n" if crlf_count >= lf_count else "\n"
        return text.splitlines(keepends=True), eol

    @staticmethod
    def _write_lines(path: Path, lines):
        """
        Write lines back to disk using raw bytes — bypasses Python's text-mode
        \n→\r\n translation on Windows, which would double every \r\n ending.
        """
        import shutil as _sh
        bak = path.with_suffix(path.suffix + ".bak")
        _sh.copy2(path, bak)
        # write_bytes preserves whatever endings are already in the lines
        path.write_bytes("".join(lines).encode("utf-8"))

    def _file_replace_in_line(self, path: Path, line_no: int, old: str, new: str) -> str:
        """
        Replace the first occurrence of `old` with `new` on 1-indexed line `line_no`.
        The match is done against the stripped line content so leading/trailing
        whitespace and EOL chars don't affect the search.
        Returns a spoken result message.
        """
        lines, _ = self._read_lines(path)
        idx = line_no - 1
        if idx < 0 or idx >= len(lines):
            return f"Line {line_no} does not exist in this file (file has {len(lines)} lines)."

        original = lines[idx]
        # Strip only the EOL chars for matching, keep indent intact
        eol = ""
        stripped = original
        for ending in ("\r\n", "\n", "\r"):
            if original.endswith(ending):
                eol = ending
                stripped = original[: -len(ending)]
                break

        # If user intended to replace the whole content of the line
        if old.lower().strip() in ("content", "the content", "code", "the code", "text", "the text", "everything", "whole line", "entire line"):
            self.vscode.apply_edit(path, line_no, line_no, new)
            return f"Done. Replaced line {line_no} with: {new}"

        target_old = old
        if target_old not in stripped:
            # Try without quotes if user or STT added quotes
            unquoted = target_old.strip("'\"")
            if unquoted and unquoted in stripped:
                target_old = unquoted
            elif target_old.lower() in stripped.lower():
                # Case-insensitive substring match
                ci_idx = stripped.lower().find(target_old.lower())
                target_old = stripped[ci_idx:ci_idx + len(target_old)]
            elif unquoted and unquoted.lower() in stripped.lower():
                ci_idx = stripped.lower().find(unquoted.lower())
                target_old = stripped[ci_idx:ci_idx + len(unquoted)]
            else:
                return f"I could not find '{old}' on line {line_no}. Line contains: {stripped.strip()!r}"

        replaced = stripped.replace(target_old, new, 1)
        lines[idx] = replaced + eol
        self._write_lines(path, lines)
        logger.info(f"Replaced '{target_old}' → '{new}' on line {line_no} of {path.name}")
        return f"Done. Replaced '{target_old}' with '{new}' on line {line_no}."

    def _file_delete_lines(self, path: Path, start: int, end: int) -> bool:
        """Delete 1-indexed lines start..end inclusive. Returns True on success."""
        try:
            lines, _ = self._read_lines(path)
            idx_s = max(0, start - 1)
            idx_e = min(len(lines), end)   # slice end is exclusive so `end` not `end-1`
            if idx_s >= len(lines):
                return False
            del lines[idx_s:idx_e]
            self._write_lines(path, lines)
            logger.info(f"Deleted lines {start}-{end} from {path.name}")
            return True
        except Exception as e:
            logger.error(f"_file_delete_lines failed: {e}")
            return False

    def _file_insert_line(self, path: Path, line_no: int, text: str, after: bool) -> bool:
        """
        Insert `text` as a new line after or before 1-indexed line `line_no`.
        Uses the file's native EOL style so the inserted line doesn't corrupt endings.
        Preserves the indentation of the reference line.
        """
        try:
            lines, eol = self._read_lines(path)
            idx = line_no - 1
            if idx < 0 or idx > len(lines):
                return False
            ref_line = lines[idx] if idx < len(lines) else ""
            # Count leading whitespace chars (don't count \r or \n)
            indent = len(ref_line) - len(ref_line.lstrip(" \t"))
            new_line = " " * indent + text.strip() + eol
            insert_at = idx + 1 if after else idx
            lines.insert(insert_at, new_line)
            self._write_lines(path, lines)
            logger.info(f"Inserted line {'after' if after else 'before'} {line_no} in {path.name}")
            return True
        except Exception as e:
            logger.error(f"_file_insert_line failed: {e}")
            return False

    def _file_toggle_comment(self, path: Path, line_no: int, add_comment: bool) -> bool:
        """Add or remove a leading comment character on 1-indexed line `line_no`."""
        try:
            lines, eol = self._read_lines(path)
            idx = line_no - 1
            if idx < 0 or idx >= len(lines):
                return False

            original = lines[idx]
            # Separate trailing EOL from content
            line_eol = ""
            content_raw = original
            for ending in ("\r\n", "\n", "\r"):
                if original.endswith(ending):
                    line_eol = ending
                    content_raw = original[: -len(ending)]
                    break

            stripped = content_raw.lstrip()
            indent = content_raw[: len(content_raw) - len(stripped)]

            # Detect comment style from file extension
            suffix = path.suffix.lower()
            if suffix in (".js", ".ts", ".jsx", ".tsx", ".java", ".c", ".cpp",
                          ".cs", ".go", ".swift", ".rs", ".kt"):
                char = "//"
            elif suffix in (".html", ".xml"):
                return False   # too complex for a simple toggle
            else:
                char = "#"     # Python, shell, YAML, Ruby, TOML, etc.

            if add_comment:
                if not stripped.startswith(char):
                    lines[idx] = f"{indent}{char} {stripped}{line_eol}"
            else:
                if stripped.startswith(char + " "):
                    lines[idx] = f"{indent}{stripped[len(char)+1:]}{line_eol}"
                elif stripped.startswith(char):
                    lines[idx] = f"{indent}{stripped[len(char):]}{line_eol}"

            self._write_lines(path, lines)
            logger.info(f"{'Commented' if add_comment else 'Uncommented'} line {line_no} in {path.name}")
            return True
        except Exception as e:
            logger.error(f"_file_toggle_comment failed: {e}")
            return False
