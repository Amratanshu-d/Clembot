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


class TestSTTCorruption(unittest.TestCase):
    """Tests for code-command STT corruption correction."""

    def setUp(self):
        self.n = SpeechNormalizer()

    # ── HOMOPHONE_MAP corrections ────────────────────────────────────────────

    def test_showero_line(self):
        """'showero line 32' → 'show line 32'"""
        result = self.n.normalize_command("showero line 32")
        self.assertIn("show", result.lower())
        self.assertIn("line", result.lower())
        self.assertIn("32", result)

    def test_showo_line(self):
        result = self.n.normalize_command("showo line 5")
        self.assertIn("show", result.lower())

    def test_showro_line(self):
        result = self.n.normalize_command("showro line 10")
        self.assertIn("show", result.lower())

    def test_delet_line(self):
        """'delet line 5' → 'delete line 5'"""
        result = self.n.normalize_command("delet line 5")
        self.assertIn("delete", result.lower())

    def test_deleet_line(self):
        result = self.n.normalize_command("deleet line 7")
        self.assertIn("delete", result.lower())

    def test_insertt_at_line(self):
        """'insertt at line 3' → 'insert at line 3'"""
        result = self.n.normalize_command("insertt at line 3")
        self.assertIn("insert", result.lower())

    def test_replays_word(self):
        """'replays hello with world' → 'replace hello with world'"""
        result = self.n.normalize_command("replays hello with world")
        self.assertIn("replace", result.lower())

    def test_un_comment_line(self):
        """'un comment line 8' → 'uncomment line 8'"""
        result = self.n.normalize_command("un comment line 8")
        self.assertIn("uncomment", result.lower())

    def test_gotto_line(self):
        """'gotto line 20' → 'go to line 20'"""
        result = self.n.normalize_command("gotto line 20")
        self.assertIn("go to", result.lower())

    def test_lion_for_line(self):
        """'for lion 9 change the content to print(hello)' → has 'line'"""
        result = self.n.normalize_command("for lion 9 change the content to print(hello)")
        self.assertIn("line", result.lower())
        self.assertNotIn("lion", result.lower())

    def test_lyine_for_line(self):
        result = self.n.normalize_command("show lyine 15")
        self.assertIn("line", result.lower())

    def test_commet(self):
        result = self.n.normalize_command("commet line 4")
        self.assertIn("comment", result.lower())

    # ── Regex token-repair pass ──────────────────────────────────────────────

    def test_regex_showero(self):
        """Regex pass catches garbled 'showero' even without exact dict entry."""
        result = self.n.fix_code_command_tokens("showero line 32")
        self.assertIn("show", result.lower())

    def test_regex_line_lion(self):
        result = self.n.fix_code_command_tokens("lion 32")
        self.assertIn("line", result.lower())

    def test_regex_go_to_gotto(self):
        result = self.n.fix_code_command_tokens("gotto line 5")
        self.assertIn("go to", result.lower())

    def test_spoken_digit_thirty_2(self):
        """'thirty 2' → 'thirty two' via lambda replacement."""
        result = self.n.normalize_command("show line thirty 2")
        self.assertIn("thirty two", result.lower())

    def test_hyphenated_digit_thirty_two(self):
        """'thirty-two' → 'thirty two' via homophone map."""
        result = self.n.normalize_command("show line thirty-two")
        self.assertIn("thirty two", result.lower())

    def test_full_pipeline_showero(self):
        """End-to-end: 'please showero line 32' → 'show line 32'"""
        result = self.n.normalize_command("please showero line 32")
        self.assertEqual(result.lower(), "show line 32")

    def test_full_pipeline_lion_digit(self):
        """End-to-end: 'for lion 9 change content to x' has 'line 9'"""
        result = self.n.normalize_command("for lion 9 change content to x")
        self.assertIn("line", result.lower())
        self.assertIn("9", result)


if __name__ == "__main__":
    unittest.main()
