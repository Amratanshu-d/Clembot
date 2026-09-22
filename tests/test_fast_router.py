import unittest
from app.commands.fast_router import FastCommandRouter


class TestFastCommandRouter(unittest.TestCase):
    def setUp(self):
        self.router = FastCommandRouter()

    def test_window_commands(self):
        plan = self.router.plan_for_command("minimize the current window")
        self.assertIsNotNone(plan)
        self.assertEqual(plan.actions[0].type, "window_minimize")

        plan = self.router.plan_for_command("maximize this window")
        self.assertIsNotNone(plan)
        self.assertEqual(plan.actions[0].type, "window_maximize")

        plan = self.router.plan_for_command("snap window left")
        self.assertIsNotNone(plan)
        self.assertEqual(plan.actions[0].type, "window_snap_left")

    def test_file_folder_commands(self):
        plan = self.router.plan_for_command("open downloads")
        self.assertIsNotNone(plan)
        self.assertEqual(plan.actions[0].type, "open_folder")
        self.assertEqual(plan.actions[0].path, "Downloads")

        plan = self.router.plan_for_command("create a new folder called AI Projects")
        self.assertIsNotNone(plan)
        self.assertEqual(plan.actions[0].type, "create_folder")
        self.assertEqual(plan.actions[0].path, "AI Projects")

        plan = self.router.plan_for_command("create a file called notes.txt")
        self.assertIsNotNone(plan)
        self.assertEqual(plan.actions[0].type, "create_file")
        self.assertEqual(plan.actions[0].path, "notes.txt")

    def test_directory_listing_command(self):
        plan = self.router.plan_for_command("What files are in Downloads?")
        self.assertIsNotNone(plan)
        self.assertEqual(plan.actions[0].type, "list_directory")
        self.assertEqual(plan.actions[0].path.lower(), "downloads")

    def test_app_and_search_commands(self):
        plan = self.router.plan_for_command("open chrome")
        self.assertIsNotNone(plan)
        self.assertEqual(plan.actions[0].type, "open_app")
        self.assertEqual(plan.actions[0].app, "chrome")

        plan = self.router.plan_for_command("Search Google for Python Django tutorials")
        self.assertIsNotNone(plan)
        self.assertEqual(plan.actions[0].type, "web_search")
        self.assertEqual(plan.actions[0].query, "Python Django tutorials")

    def test_editor_navigation(self):
        plan = self.router.plan_for_command("go to line 25")
        self.assertIsNotNone(plan)
        self.assertEqual(plan.actions[0].type, "vscode_jump_line")
        self.assertEqual(plan.actions[0].line_number, 25)

    def test_question_and_distance_search(self):
        # User reported: "tell distance from satna to jabalpur"
        plan = self.router.plan_for_command("tell distance from satna to jabalpur")
        self.assertIsNotNone(plan)
        self.assertEqual(plan.actions[0].type, "web_search")
        self.assertIn("satna", plan.actions[0].query)

        plan = self.router.plan_for_command("what is artificial intelligence")
        self.assertIsNotNone(plan)
        self.assertEqual(plan.actions[0].type, "web_search")

    def test_enhanced_openings(self):
        # Drives
        plan = self.router.plan_for_command("open f drive")
        self.assertIsNotNone(plan)
        self.assertEqual(plan.actions[0].type, "open_folder")
        self.assertEqual(plan.actions[0].path, "F:\\")

        # Explicit folder
        plan = self.router.plan_for_command("open folder projects")
        self.assertIsNotNone(plan)
        self.assertEqual(plan.actions[0].type, "open_folder")
        self.assertEqual(plan.actions[0].path, "projects")

        # Explicit file
        plan = self.router.plan_for_command("open file notes.txt")
        self.assertIsNotNone(plan)
        self.assertEqual(plan.actions[0].type, "open_file")
        self.assertEqual(plan.actions[0].path, "notes.txt")

        # Extension detection
        plan = self.router.plan_for_command("open report.pdf")
        self.assertIsNotNone(plan)
        self.assertEqual(plan.actions[0].type, "open_file")
        self.assertEqual(plan.actions[0].path, "report.pdf")

    def test_close_file_and_tab_commands(self):
        # Active file close
        for phrase in ["close this file", "close file", "close active file", "close current file", "close file in vscode", "close vscode file"]:
            plan = self.router.plan_for_command(phrase)
            self.assertIsNotNone(plan, f"Failed for phrase: {phrase}")
            self.assertEqual(plan.actions[0].type, "vscode_close_file", f"Failed action type for {phrase}")

        # Named file close
        plan = self.router.plan_for_command("close main.py")
        self.assertIsNotNone(plan)
        self.assertEqual(plan.actions[0].type, "vscode_close_file")
        self.assertEqual(plan.actions[0].path, "main.py")

        plan = self.router.plan_for_command("close file test.py")
        self.assertIsNotNone(plan)
        self.assertEqual(plan.actions[0].type, "vscode_close_file")
        self.assertEqual(plan.actions[0].path, "test.py")

        # Close app
        plan = self.router.plan_for_command("close vscode")
        self.assertIsNotNone(plan)
        self.assertEqual(plan.actions[0].type, "close_app")
        self.assertEqual(plan.actions[0].app, "vscode")

    def test_fast_router_code_edits(self):
        cases = [
            ("in line 36 replace with from what", "REPLACE_IN_LINE:36:with::what"),
            ("inline 43 replace I with J", "REPLACE_IN_LINE:43:I::J"),
            ("line 36 replace with from what", "REPLACE_IN_LINE:36:with::what"),
            ("line 43 replace I with J", "REPLACE_IN_LINE:43:I::J"),
            ("in line 36 replace with x = 10", "REPLACE_LINE:36::x = 10"),
            ("drop line 36", "DELETE_LINE:36"),
        ]
        for cmd, expected_token in cases:
            plan = self.router.plan_for_command(cmd)
            self.assertIsNotNone(plan, f"Failed for cmd: {cmd}")
            self.assertEqual(plan.actions[0].type, "vscode_edit")
            self.assertEqual(plan.actions[0].text, expected_token)


if __name__ == "__main__":
    unittest.main()
