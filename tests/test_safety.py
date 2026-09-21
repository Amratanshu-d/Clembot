import unittest
from pathlib import Path
from app.core.models import AgentAction
from app.security.guard import SecurityGuard


class TestSecurityGuard(unittest.TestCase):
    def setUp(self):
        self.guard = SecurityGuard()

    def test_protected_windows_paths(self):
        self.assertTrue(self.guard.is_protected_path(Path("C:\\Windows")))
        self.assertTrue(self.guard.is_protected_path(Path("C:\\Windows\\System32")))
        self.assertTrue(self.guard.is_protected_path(Path("C:\\Program Files")))
        self.assertTrue(self.guard.is_protected_path(Path("C:\\")))
        self.assertFalse(self.guard.is_protected_path(Path.home() / "Desktop" / "my_project"))

    def test_dangerous_shell_commands_blocked(self):
        is_safe, msg = self.guard.validate_shell_command("format c:")
        self.assertFalse(is_safe)

        is_safe, msg = self.guard.validate_shell_command("rmdir /s /q c:\\")
        self.assertFalse(is_safe)

        is_safe, msg = self.guard.validate_shell_command("python app.py")
        self.assertTrue(is_safe)

    def test_confirmation_triggered_for_protected_path_deletion(self):
        action = AgentAction(type="trash_path", path="C:\\Windows\\System32")
        requires_conf, conf_req = self.guard.evaluate_action_risk(action)
        self.assertTrue(requires_conf)
        self.assertEqual(conf_req.risk_level, "critical")
        self.assertIn("protected Windows system path", conf_req.prompt)

    def test_confirmation_triggered_for_terminal_commands(self):
        action = AgentAction(type="terminal_run", command="pip install django")
        requires_conf, conf_req = self.guard.evaluate_action_risk(action)
        self.assertTrue(requires_conf)
        self.assertIn("confirm", conf_req.prompt.lower())


if __name__ == "__main__":
    unittest.main()
