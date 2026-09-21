import unittest
from app.speech.wake_word import WakeWordDetector


class TestWakeWordDetector(unittest.TestCase):
    def setUp(self):
        self.detector = WakeWordDetector()

    def test_activation_phrases(self):
        # Specific user requirement: "the voice assistant will get activated when the user say 'Clembot activate yourself'"
        is_wake, cmd = self.detector.check_activation("Clembot activate yourself")
        self.assertTrue(is_wake)
        self.assertIsNone(cmd)

        is_wake, cmd = self.detector.check_activation("Clembot activate yourself and open my Downloads")
        self.assertTrue(is_wake)
        self.assertEqual(cmd, "open my downloads")

        is_wake, cmd = self.detector.check_activation("Hey Clembot")
        self.assertTrue(is_wake)

    def test_deactivation_phrases(self):
        # Specific user requirement: "the voice assistant will turn off on saying 'Clembot deactivate'"
        is_sleep = self.detector.check_deactivation("Clembot deactivate")
        self.assertTrue(is_sleep)

        is_sleep = self.detector.check_deactivation("Clembot deactivate yourself")
        self.assertTrue(is_sleep)

        is_sleep = self.detector.check_deactivation("clembot sleep")
        self.assertTrue(is_sleep)

        # Normal command should not deactivate
        self.assertFalse(self.detector.check_deactivation("open downloads"))

    def test_phonetic_variations(self):
        # User reported: "clemburt", "clem ber", "clembur"
        is_wake, cmd = self.detector.check_activation("clemburt activate yourself")
        self.assertTrue(is_wake)

        is_wake, cmd = self.detector.check_activation("clembur activate yourself and open downloads")
        self.assertTrue(is_wake)
        self.assertEqual(cmd, "open downloads")

        is_sleep = self.detector.check_deactivation("clem ber deactivate")
        self.assertTrue(is_sleep)

        is_sleep = self.detector.check_deactivation("clembur deactivate")
        self.assertTrue(is_sleep)

        # Strip wake word with phonetic mis-transcription
        stripped = self.detector.strip_wake_phrase("clemburt open vscode")
        self.assertEqual(stripped, "open vscode")


if __name__ == "__main__":
    unittest.main()
