import unittest
from app.commands.friendly_errors import FriendlyErrorTranslator
from app.commands.router import ActionRouter
from app.core.models import AgentAction


class TestFriendlyErrors(unittest.TestCase):
    def setUp(self):
        self.translator = FriendlyErrorTranslator()
        self.router = ActionRouter()

    def test_translate_file_not_found_explorer(self):
        action = AgentAction(type="open_file", path="explorer")
        err = FileNotFoundError("File not found: F:\\intr\\voiceps\\explorer")
        msg = self.translator.translate(err, action)
        self.assertIn("File Explorer", msg)

    def test_translate_file_not_found_postgresql(self):
        action = AgentAction(type="open_app", app="post grey sql")
        err = FileNotFoundError("I could not find an application named 'post grey sql' on this PC.")
        msg = self.translator.translate(err, action)
        self.assertIn("PostgreSQL", msg)

    def test_translate_file_not_found_regular(self):
        action = AgentAction(type="open_file", path="non_existent_report.pdf")
        err = FileNotFoundError("File not found: non_existent_report.pdf")
        msg = self.translator.translate(err, action)
        self.assertIn("non_existent_report.pdf", msg)

    def test_translate_permission_error(self):
        action = AgentAction(type="trash_path", path="C:\\Windows\\System32")
        err = PermissionError("Access is denied")
        msg = self.translator.translate(err, action)
        self.assertIn("denied access", msg)

    def test_translate_file_exists_error(self):
        action = AgentAction(type="create_file", path="notes.txt")
        err = FileExistsError("File already exists")
        msg = self.translator.translate(err, action)
        self.assertIn("already exists", msg)

    def test_translate_timeout_error(self):
        action = AgentAction(type="web_search", query="test")
        err = TimeoutError("Connection timed out")
        msg = self.translator.translate(err, action)
        self.assertIn("timed out", msg)

    def test_router_returns_friendly_message_on_failure(self):
        # Action that will fail with FileNotFoundError
        action = AgentAction(type="trash_path", path="C:\\non_existent_dir_99999\\fake.txt")
        result = self.router.execute(action)
        self.assertFalse(result.success)
        self.assertIn("couldn't find", result.message)


if __name__ == "__main__":
    unittest.main()
