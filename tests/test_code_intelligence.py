import shutil
import tempfile
import unittest
from pathlib import Path
from app.editor.code_intelligence import CodeIntelligenceEngine


class TestCodeIntelligenceEngine(unittest.TestCase):
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp(prefix="clembot_test_code_"))

    def tearDown(self):
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_find_python_function_range(self):
        code = """import os

def calculate_total(items):
    total = sum(items)
    return total

def other():
    pass
"""
        res = CodeIntelligenceEngine.find_python_function_range(code, "calculate_total")
        self.assertIsNotNone(res)
        start_line, end_line, func_src = res
        self.assertEqual(start_line, 3)
        self.assertIn("calculate_total", func_src)

    def test_propose_function_rename(self):
        sample_file = self.temp_dir / "calc.py"
        sample_file.write_text("def calculate_total(a):\n    return a\nval = calculate_total(5)\n", encoding="utf-8")

        proposal = CodeIntelligenceEngine.propose_function_rename(sample_file, "calculate_total", "calculate_price")
        self.assertIsNotNone(proposal)
        self.assertIn("calculate_price", proposal.proposed_code)
        self.assertIn("-def calculate_total", proposal.diff)
        self.assertIn("+def calculate_price", proposal.diff)

        # Apply proposal
        success = CodeIntelligenceEngine.apply_proposal(proposal)
        self.assertTrue(success)
        self.assertIn("calculate_price", sample_file.read_text(encoding="utf-8"))
        # Verify backup was created
        self.assertTrue(sample_file.with_suffix(".py.bak").is_file())

    def test_propose_exception_handling(self):
        sample_file = self.temp_dir / "db.py"
        sample_file.write_text("def fetch_data():\n    db_call()\n    return True\n", encoding="utf-8")

        proposal = CodeIntelligenceEngine.propose_exception_handling_at_line(sample_file, target_line=2, line_count=1)
        self.assertIsNotNone(proposal)
        self.assertIn("try:", proposal.proposed_code)
        self.assertIn("except Exception as e:", proposal.proposed_code)


if __name__ == "__main__":
    unittest.main()
