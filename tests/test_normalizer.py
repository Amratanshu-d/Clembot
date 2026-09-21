import unittest
from app.speech.normalizer import SpeechNormalizer
from app.speech.wake_word import WakeWordDetector


class TestSpeechNormalizer(unittest.TestCase):
    def setUp(self):
        self.normalizer = SpeechNormalizer()
        self.wake_detector = WakeWordDetector()

    def test_homophone_replacements(self):
        cases = [
            ("open post grey sql", "open postgresql"),
            ("start postgre sql", "start postgresql"),
            ("open vs code", "open vscode"),
            ("launch pi charm", "launch pycharm"),
            ("open file explorer", "open explorer"),
            ("open brave browser", "open brave"),
            ("open edge browser", "open edge"),
            ("search git hub for python", "search github for python"),
            ("open task manager", "open taskmgr"),
        ]
        for inp, expected in cases:
            res = self.normalizer.replace_homophones(inp)
            self.assertEqual(res.lower(), expected.lower(), f"Failed for input: {inp}")

    def test_filler_stripping(self):
        cases = [
            ("can you please open downloads", "open downloads"),
            ("could you please check this file", "check this file"),
            ("please open vs code", "open vs code"),
            ("check carefully and delete notes.txt", "delete notes.txt"),
            ("tell me the weather", "the weather"),
            ("i want you to open desktop", "open desktop"),
            ("kindly minimize window", "minimize window"),
        ]
        for inp, expected in cases:
            res = self.normalizer.strip_fillers(inp)
            self.assertEqual(res.lower(), expected.lower(), f"Failed for input: {inp}")

    def test_end_to_end_normalization(self):
        inp = "can you please open post grey sql"
        res = self.normalizer.normalize_command(inp)
        self.assertEqual(res.lower(), "open postgresql")

        inp2 = "please open file explorer"
        res2 = self.normalizer.normalize_command(inp2)
        self.assertEqual(res2.lower(), "open explorer")

    def test_confidence_match_term(self):
        candidates = ["postgresql", "vscode", "firefox", "calculator"]
        
        # Exact or close phonetic match (Score >= 82)
        match, score, m_type = self.normalizer.match_term("postgress", candidates)
        self.assertEqual(match, "postgresql")
        self.assertEqual(m_type, "accept")
        self.assertGreaterEqual(score, 82.0)

        # High similarity match
        match, score, m_type = self.normalizer.match_term("fire fox", candidates)
        self.assertEqual(match, "firefox")
        self.assertIn(m_type, ["accept", "near_match"])
        self.assertGreaterEqual(score, 65.0)

        # Unrelated term (Score < 65)
        match, score, m_type = self.normalizer.match_term("banana", candidates)
        self.assertIsNone(match)
        self.assertEqual(m_type, "none")
        self.assertLess(score, 65.0)

    def test_fuzzy_wake_word_detection(self):
        # ASR transcriptions observed in logs
        log_cases = [
            "climbers open vs code",
            "lambert activate yourself",
            "carrom board activity yourself",
            "fake lambert activate yourself",
            "clem ber activate yourself",
            "clam bot activate yourself",
        ]

        # Check activation for activate phrases
        for phrase in log_cases[1:]:
            is_wake, _ = self.wake_detector.check_activation(phrase)
            self.assertTrue(is_wake, f"Failed to activate for phrase: {phrase}")

        # Check wake word stripping for commands
        cmd = self.wake_detector.strip_wake_phrase("climbers open vs code")
        self.assertEqual(cmd.lower(), "open vs code")

        cmd2 = self.wake_detector.strip_wake_phrase("clembur open downloads")
        self.assertEqual(cmd2.lower(), "open downloads")

        cmd3 = self.wake_detector.strip_wake_phrase("hey clembot please open desktop")
        self.assertEqual(cmd3.lower(), "open desktop")


if __name__ == "__main__":
    unittest.main()
