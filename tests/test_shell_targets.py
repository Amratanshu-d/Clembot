import unittest
from unittest.mock import patch
from app.commands.fast_router import FastCommandRouter
from app.commands.router import ActionRouter
from app.core.models import AgentAction
from app.filesystem.paths import WindowsPathResolver


class TestShellTargets(unittest.TestCase):
    def setUp(self):
        self.fast_router = FastCommandRouter()
        self.router = ActionRouter()

    def test_fast_router_shell_targets(self):
        # File Explorer
        plan = self.fast_router.plan_for_command("open file explorer")
        self.assertIsNotNone(plan)
        self.assertEqual(plan.actions[0].type, "open_app")
        self.assertEqual(plan.actions[0].app, "explorer")

        plan = self.fast_router.plan_for_command("open explorer")
        self.assertIsNotNone(plan)
        self.assertEqual(plan.actions[0].type, "open_app")
        self.assertEqual(plan.actions[0].app, "explorer")

        # This PC
        plan = self.fast_router.plan_for_command("open this pc")
        self.assertIsNotNone(plan)
        self.assertEqual(plan.actions[0].type, "open_folder")
        self.assertIn("20D04FE0", plan.actions[0].path)

        # Recycle Bin
        plan = self.fast_router.plan_for_command("open recycle bin")
        self.assertIsNotNone(plan)
        self.assertEqual(plan.actions[0].type, "open_folder")
        self.assertIn("645FF040", plan.actions[0].path)

        # Settings
        plan = self.fast_router.plan_for_command("open settings")
        self.assertIsNotNone(plan)
        self.assertEqual(plan.actions[0].type, "open_url")
        self.assertEqual(plan.actions[0].url, "ms-settings:")

        # Task Manager
        plan = self.fast_router.plan_for_command("open task manager")
        self.assertIsNotNone(plan)
        self.assertEqual(plan.actions[0].type, "open_app")
        self.assertEqual(plan.actions[0].app, "taskmgr")

        # Control Panel
        plan = self.fast_router.plan_for_command("open control panel")
        self.assertIsNotNone(plan)
        self.assertEqual(plan.actions[0].type, "open_app")
        self.assertEqual(plan.actions[0].app, "control")

    def test_explicit_file_pattern_shell_interception(self):
        # Even if user or STT speaks "open file called explorer"
        plan = self.fast_router.plan_for_command("open file explorer")
        self.assertIsNotNone(plan)
        self.assertEqual(plan.actions[0].type, "open_app")
        self.assertEqual(plan.actions[0].app, "explorer")

    def test_router_open_file_fallback_to_app(self):
        # When action has type='open_file' and path='explorer', router must route to open_app
        action = AgentAction(type="open_file", path="explorer")
        with patch.object(self.router.apps, "open_or_activate", return_value="Opening explorer.") as mock_open:
            result = self.router.execute(action)
            self.assertTrue(result.success)
            self.assertEqual(result.action_type, "open_app")
            mock_open.assert_called_once_with("explorer")

    def test_paths_resolver_fallback_safety(self):
        # A non-existent file query should resolve to Desktop, not invent a file in CWD
        resolved = WindowsPathResolver.resolve_path("non_existent_fake_test_12345.txt")
        self.assertIn("Desktop", str(resolved))


if __name__ == "__main__":
    unittest.main()
