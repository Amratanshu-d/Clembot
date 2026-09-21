import unittest
from pathlib import Path
from app.memory.conversation import ConversationalMemory


class TestConversationalMemory(unittest.TestCase):
    def setUp(self):
        self.memory = ConversationalMemory()

    def test_resolve_there_to_last_folder(self):
        self.memory.add_user_turn("Open Downloads")
        self.memory.add_clembot_turn("Downloads is open", target_path=str(Path.home() / "Downloads"))

        resolved = self.memory.resolve_contextual_references("Open the PDF there")
        self.assertIn(str(Path.home() / "Downloads"), resolved)

    def test_resolve_that_file_reference(self):
        sample_file = Path.home() / "Desktop" / "app.py"
        self.memory.add_user_turn("Open app.py")
        self.memory.add_clembot_turn("app.py is open", target_file=str(sample_file))

        resolved = self.memory.resolve_contextual_references("delete it")
        self.assertIn(str(sample_file), resolved)


if __name__ == "__main__":
    unittest.main()
