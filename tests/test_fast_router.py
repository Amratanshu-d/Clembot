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

        plan = self.router.plan_for_command("jump to line forty two")
        self.assertIsNotNone(plan)
        self.assertEqual(plan.actions[0].type, "vscode_jump_line")
        self.assertEqual(plan.actions[0].line_number, 42)

    def test_show_and_read_line(self):
        # User reported: "show line 36"
        plan = self.router.plan_for_command("show line 36")
        self.assertIsNotNone(plan)
        self.assertEqual(plan.actions[0].type, "vscode_read_line")
        self.assertEqual(plan.actions[0].line_number, 36)
        self.assertIn("Showing line 36", plan.reply)

        # Compound numbers: "show me line thirty six"
        plan = self.router.plan_for_command("show me line thirty six")
        self.assertIsNotNone(plan)
        self.assertEqual(plan.actions[0].type, "vscode_read_line")
        self.assertEqual(plan.actions[0].line_number, 36)

        # Synonyms: display, view
        plan = self.router.plan_for_command("display line 10")
        self.assertIsNotNone(plan)
        self.assertEqual(plan.actions[0].type, "vscode_read_line")
        self.assertEqual(plan.actions[0].line_number, 10)

        plan = self.router.plan_for_command("view line 15")
        self.assertIsNotNone(plan)
        self.assertEqual(plan.actions[0].type, "vscode_read_line")
        self.assertEqual(plan.actions[0].line_number, 15)

        # Read line
        plan = self.router.plan_for_command("read line 20")
        self.assertIsNotNone(plan)
        self.assertEqual(plan.actions[0].type, "vscode_read_line")
        self.assertEqual(plan.actions[0].line_number, 20)
        self.assertIn("Reading line 20", plan.reply)

        # With file
        plan = self.router.plan_for_command("show line 50 in main.py")
        self.assertIsNotNone(plan)
        self.assertEqual(plan.actions[0].type, "vscode_read_line")
        self.assertEqual(plan.actions[0].line_number, 50)
        self.assertEqual(plan.actions[0].path, "main.py")

        # User reported Google STT corruptions: "Shoreline 22", "Shoreline 42"
        plan = self.router.plan_for_command("shoreline 22")
        self.assertIsNotNone(plan)
        self.assertEqual(plan.actions[0].type, "vscode_read_line")
        self.assertEqual(plan.actions[0].line_number, 22)

        plan = self.router.plan_for_command("shoreline 42")
        self.assertIsNotNone(plan)
        self.assertEqual(plan.actions[0].type, "vscode_read_line")
        self.assertEqual(plan.actions[0].line_number, 42)

        plan = self.router.plan_for_command("showline 36")
        self.assertIsNotNone(plan)
        self.assertEqual(plan.actions[0].type, "vscode_read_line")
        self.assertEqual(plan.actions[0].line_number, 36)

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

    def test_open_file_routing(self):
        """Files with extensions should route to open_file, not open_app."""
        cases = [
            "open myfile.txt",
            "open report.pdf",
            "open script.py",
            "open notes.md",
            "open data.csv",
            "open main.cpp",
        ]
        for cmd in cases:
            plan = self.router.plan_for_command(cmd)
            self.assertIsNotNone(plan, f"No plan for: {cmd}")
            self.assertEqual(
                plan.actions[0].type, "open_file",
                f"'{cmd}' routed to {plan.actions[0].type!r} instead of open_file"
            )

    def test_open_explicit_file_command(self):
        """'open file <name>' pattern should always give open_file."""
        cases = [
            ("open file notes.txt", "notes.txt"),
            ("open the file resume.pdf", "resume.pdf"),
            ("open file main.py", "main.py"),
        ]
        for cmd, expected_path in cases:
            plan = self.router.plan_for_command(cmd)
            self.assertIsNotNone(plan, f"No plan for: {cmd}")
            self.assertEqual(plan.actions[0].type, "open_file",
                             f"'{cmd}' routed to {plan.actions[0].type!r}")
            self.assertEqual(plan.actions[0].path, expected_path,
                             f"Path mismatch for '{cmd}'")

    def test_save_file_routing(self):
        """All 'save ...' variants should produce a save action, not web search."""
        cases = [
            "save",
            "save this file",
            "save the file",
            "save file",
            "save the file main.py",
            "save this code",
            "save my work",
        ]
        for cmd in cases:
            plan = self.router.plan_for_command(cmd)
            self.assertIsNotNone(plan, f"No plan for: {cmd}")
            self.assertEqual(
                plan.actions[0].type, "save",
                f"'{cmd}' routed to {plan.actions[0].type!r} instead of save"
            )


if __name__ == "__main__":
    unittest.main()
