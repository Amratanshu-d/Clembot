"""
tests/test_vscode_jump.py

Unit tests for:
  1. ActionRouter: vscode_read_line calls jump_to_line AND reads line content.
  2. ActionRouter: vscode_read_line with path opens file at line.
  3. VSCodeAdapter: jump_to_line multi-layer fallback (IPC -> CLI -> Hotkey).
  4. LocalHeuristicPlanner: handles 'show line N' and 'go to line N'.
"""

import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from app.commands.router import ActionRouter
from app.core.models import AgentAction, ScreenContext
from app.editor.vscode_adapter import VSCodeAdapter
from app.ai.local_heuristic import LocalHeuristicPlanner


class TestVSCodeJumpAndReadLine(unittest.TestCase):
    def setUp(self):
        self.router = ActionRouter()

    def test_vscode_read_line_calls_jump_to_line(self):
        """vscode_read_line must scroll/jump to the line in VS Code AND return line text."""
        with patch.object(self.router.vscode, "jump_to_line", return_value=True) as mock_jump, \
             patch.object(self.router.vscode, "read_document", return_value="line 1\nline 2\nresult = x + y\nline 4"):

            action = AgentAction(type="vscode_read_line", line_number=3)
            result = self.router.execute(action)

            mock_jump.assert_called_once_with(3)
            self.assertTrue(result.success)
            self.assertIn("Line 3 says: result = x + y", result.message)

    def test_vscode_read_line_nonexistent_line(self):
        """vscode_read_line reports when line does not exist, but still jumps."""
        with patch.object(self.router.vscode, "jump_to_line", return_value=True) as mock_jump, \
             patch.object(self.router.vscode, "read_document", return_value="line 1\nline 2"):

            action = AgentAction(type="vscode_read_line", line_number=10)
            result = self.router.execute(action)

            mock_jump.assert_called_once_with(10)
            self.assertTrue(result.success)
            self.assertIn("Line 10 does not exist", result.message)

    def test_vscode_read_line_document_unread(self):
        """When document cannot be read, still jumps and returns friendly message."""
        with patch.object(self.router.vscode, "jump_to_line", return_value=True) as mock_jump, \
             patch.object(self.router.vscode, "read_document", return_value=None):

            action = AgentAction(type="vscode_read_line", line_number=36)
            result = self.router.execute(action)

            mock_jump.assert_called_once_with(36)
            self.assertTrue(result.success)
            self.assertIn("Showing line 36 in VS Code", result.message)

    def test_vscode_read_line_with_path(self):
        """When a path is provided, opens file at line."""
        fake_path = Path("fake_script.py")
        with patch("app.filesystem.paths.WindowsPathResolver.resolve", return_value=fake_path), \
             patch.object(Path, "is_file", return_value=True), \
             patch.object(self.router.vscode, "open_file", return_value=True) as mock_open, \
             patch.object(self.router.vscode, "read_document", return_value="print('hello')"):

            action = AgentAction(type="vscode_read_line", line_number=1, path="fake_script.py")
            result = self.router.execute(action)

            mock_open.assert_called_once_with(fake_path, line_number=1)
            self.assertTrue(result.success)
            self.assertIn("Line 1 says: print('hello')", result.message)


class TestVSCodeAdapterJumpLayers(unittest.TestCase):
    def setUp(self):
        self.adapter = VSCodeAdapter()

    def test_layer1_ipc_success(self):
        """When IPC extension is connected, jump_to_line uses IPC post."""
        with patch.object(self.adapter, "is_available", return_value=True), \
             patch("app.editor.vscode_adapter._ipc_post", return_value={"success": True}) as mock_post, \
             patch("app.windows.apps.WindowsAppCatalog.activate_running_window"):

            success = self.adapter.jump_to_line(42)
            self.assertTrue(success)
            mock_post.assert_called_once()
            call_args = mock_post.call_args[0]
            self.assertEqual(call_args[0], "/vscode/enqueue_command")
            self.assertEqual(call_args[1]["action"], "jump_to_line")
            self.assertEqual(call_args[1]["params"]["line_number"], 42)

    def test_layer2_cli_goto(self):
        """When IPC unavailable but active file known, uses CLI --goto."""
        fake_file = Path("C:/project/app.py")
        with patch.object(self.adapter, "is_available", return_value=False), \
             patch.object(self.adapter, "get_active_file", return_value=fake_file), \
             patch.object(self.adapter, "_get_code_cli", return_value="code.cmd"), \
             patch("subprocess.Popen") as mock_popen, \
             patch("app.windows.apps.WindowsAppCatalog.activate_running_window"):

            success = self.adapter.jump_to_line(15)
            self.assertTrue(success)
            mock_popen.assert_called_once()
            args = mock_popen.call_args[0][0]
            self.assertIn("code.cmd", args)
            self.assertIn("--goto", args)
            self.assertIn("C:\\project\\app.py:15", args[3] if len(args) > 3 else "")

    def test_layer3_hotkey_fallback(self):
        """When IPC unavailable and active file unknown, falls back to Ctrl+G hotkey."""
        with patch.object(self.adapter, "is_available", return_value=False), \
             patch.object(self.adapter, "get_active_file", return_value=None), \
             patch("app.windows.apps.WindowsAppCatalog.activate_running_window") as mock_activate, \
             patch("app.automation.input_adapter.WindowsInputAdapter.hotkey") as mock_hotkey, \
             patch("app.automation.input_adapter.WindowsInputAdapter.type_text") as mock_type, \
             patch("app.automation.input_adapter.WindowsInputAdapter.press_key") as mock_press:

            success = self.adapter.jump_to_line(36)
            self.assertTrue(success)
            mock_activate.assert_called()
            mock_hotkey.assert_called_with(["ctrl", "g"])
            mock_type.assert_called_with("36")
            mock_press.assert_called_with("enter")


class TestLocalHeuristicShowLine(unittest.TestCase):
    def setUp(self):
        self.planner = LocalHeuristicPlanner()
        self.ctx = ScreenContext()

    def test_show_line_heuristic(self):
        plan = self.planner.plan("show line 36", self.ctx)
        self.assertEqual(len(plan.actions), 1)
        self.assertEqual(plan.actions[0].type, "vscode_read_line")
        self.assertEqual(plan.actions[0].line_number, 36)
        self.assertIn("Showing line 36", plan.reply)

    def test_go_to_line_heuristic(self):
        plan = self.planner.plan("go to line 45", self.ctx)
        self.assertEqual(len(plan.actions), 1)
        self.assertEqual(plan.actions[0].type, "vscode_jump_line")
        self.assertEqual(plan.actions[0].line_number, 45)

    def test_shoreline_heuristic(self):
        plan = self.planner.plan("shoreline 22", self.ctx)
        self.assertEqual(len(plan.actions), 1)
        self.assertEqual(plan.actions[0].type, "vscode_read_line")
        self.assertEqual(plan.actions[0].line_number, 22)

        plan = self.planner.plan("shoreline 42", self.ctx)
        self.assertEqual(len(plan.actions), 1)
        self.assertEqual(plan.actions[0].type, "vscode_read_line")
        self.assertEqual(plan.actions[0].line_number, 42)


if __name__ == "__main__":
    unittest.main()
