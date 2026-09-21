import unittest
from app.doctor import SystemDoctor


class TestSystemDoctor(unittest.TestCase):
    def test_python_version_check(self):
        ok, msg = SystemDoctor.check_python_version()
        self.assertTrue(ok)
        self.assertIn("Python", msg)

    def test_packages_check(self):
        results = SystemDoctor.check_packages()
        self.assertGreater(len(results), 0)
        # All required critical packages should be True
        for pkg, ok, msg in results:
            self.assertTrue(ok, f"Package {pkg} failed check: {msg}")

    def test_tts_engine_check(self):
        ok, msg = SystemDoctor.check_tts_engine()
        self.assertTrue(ok)
        self.assertIn("voice engine", msg)

    def test_ipc_port_check(self):
        ok, msg = SystemDoctor.check_ipc_port()
        self.assertTrue(ok)

    def test_ai_provider_check(self):
        ok, msg = SystemDoctor.check_ai_provider()
        self.assertTrue(ok)


if __name__ == "__main__":
    unittest.main()
