import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from app.core.models import AgentAction
from app.editor.vscode_adapter import VSCodeAdapter
from app.filesystem.paths import WindowsPathResolver
from app.commands.fast_router import FastCommandRouter
from app.commands.router import ActionRouter
from app.ai.local_heuristic import LocalHeuristicPlanner
from app.speech.normalizer import SpeechNormalizer


class TestVSCodeWorkspaceOpen(unittest.TestCase):
    def setUp(self):
        # Create temporary workspace structure:
        # temp_ws/
        #   subfolder/
        #     main.py
        #     sibling.txt
        #     deep/
        #       data.md
        #   other_folder/
        #     script.py
        self.test_dir = tempfile.mkdtemp(prefix="clembot_test_ws_")
        self.ws_path = Path(self.test_dir)
        self.subfolder = self.ws_path / "subfolder"
        self.subfolder.mkdir()
        self.main_file = self.subfolder / "main.py"
        self.main_file.write_text("print('hello')", encoding="utf-8")
        self.sibling_file = self.subfolder / "sibling.txt"
        self.sibling_file.write_text("sibling data", encoding="utf-8")
        
        self.deep_dir = self.subfolder / "deep"
        self.deep_dir.mkdir()
        self.data_file = self.deep_dir / "data.md"
        self.data_file.write_text("# Documentation", encoding="utf-8")

        self.other_folder = self.ws_path / "other_folder"
        self.other_folder.mkdir()
        self.script_file = self.other_folder / "script.py"
        self.script_file.write_text("x = 10", encoding="utf-8")

        self.adapter = VSCodeAdapter()
        VSCodeAdapter._cached_workspace = self.ws_path
        VSCodeAdapter._cached_file = self.main_file

        self.p1 = patch.object(VSCodeAdapter, "get_active_file", return_value=self.main_file)
        self.p2 = patch.object(VSCodeAdapter, "get_workspace", return_value=self.ws_path)
        self.p1.start()
        self.p2.start()

    def tearDown(self):
        self.p1.stop()
        self.p2.stop()
        VSCodeAdapter._cached_workspace = None
        VSCodeAdapter._cached_file = None
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_find_in_workspace_sibling(self):
        found = self.adapter.find_in_workspace("sibling.txt")
        self.assertIsNotNone(found)
        self.assertEqual(found.resolve(), self.sibling_file.resolve())

    def test_find_in_workspace_with_spoken_prefix(self):
        found = self.adapter.find_in_workspace("the file sibling.txt")
        self.assertIsNotNone(found)
        self.assertEqual(found.resolve(), self.sibling_file.resolve())

    def test_find_in_workspace_folder(self):
        found = self.adapter.find_in_workspace("other_folder", search_files=False, search_folders=True)
        self.assertIsNotNone(found)
        self.assertEqual(found.resolve(), self.other_folder.resolve())

    def test_find_in_workspace_deep_file(self):
        found = self.adapter.find_in_workspace("data.md")
        self.assertIsNotNone(found)
        self.assertEqual(found.resolve(), self.data_file.resolve())

    def test_find_in_workspace_stem_match(self):
        found = self.adapter.find_in_workspace("script")
        self.assertIsNotNone(found)
        self.assertEqual(found.resolve(), self.script_file.resolve())

    def test_windows_path_resolver_uses_workspace(self):
        resolved = WindowsPathResolver.resolve("sibling.txt")
        self.assertTrue(resolved.exists())
        self.assertEqual(resolved.resolve(), self.sibling_file.resolve())

    def test_fast_router_file_with_comma(self):
        fr = FastCommandRouter()
        plan = fr.plan_for_command("open class,object.py")
        self.assertIsNotNone(plan)
        self.assertEqual(plan.actions[0].type, "open_file")
        self.assertEqual(plan.actions[0].path, "class,object.py")

    def test_fast_router_open_in_vscode_variations(self):
        fr = FastCommandRouter()
        plan1 = fr.plan_for_command("open sibling.txt in vscode")
        self.assertIsNotNone(plan1)
        self.assertEqual(plan1.actions[0].type, "vscode_open_file")
        self.assertEqual(plan1.actions[0].path, "sibling.txt")

        plan2 = fr.plan_for_command("open in vscode other_folder")
        self.assertIsNotNone(plan2)
        self.assertEqual(plan2.actions[0].type, "vscode_open_file")
        self.assertEqual(plan2.actions[0].path, "other_folder")

    def test_fast_router_next_and_previous_file(self):
        fr = FastCommandRouter()
        plan_next = fr.plan_for_command("open next file")
        self.assertIsNotNone(plan_next)
        self.assertEqual(plan_next.actions[0].type, "vscode_next_file")

        plan_prev = fr.plan_for_command("previous file")
        self.assertIsNotNone(plan_prev)
        self.assertEqual(plan_prev.actions[0].type, "vscode_prev_file")

    def test_fast_router_open_project(self):
        fr = FastCommandRouter()
        plan = fr.plan_for_command("open project subfolder")
        self.assertIsNotNone(plan)
        self.assertEqual(plan.actions[0].type, "open_folder")
        self.assertEqual(plan.actions[0].path, "subfolder")

    def test_local_heuristic_open_in_vscode(self):
        lh = LocalHeuristicPlanner()
        from app.core.models import ScreenContext
        plan = lh.plan("open data.md in vscode", ScreenContext())
        self.assertIsNotNone(plan)
        self.assertEqual(plan.actions[0].type, "vscode_open_file")
        self.assertEqual(plan.actions[0].path, "data.md")

    def test_action_router_open_workspace_file_routes_to_vscode(self):
        router = ActionRouter()
        action = AgentAction(type="open_file", path="sibling.txt")
        with patch.object(router.vscode, "open_file", return_value=True) as mock_open:
            res = router.execute(action)
            self.assertTrue(res.success)
            self.assertIn("in VS Code", res.message)
            mock_open.assert_called_once()
            called_path = mock_open.call_args[0][0]
            self.assertEqual(called_path.resolve(), self.sibling_file.resolve())

    def test_action_router_open_workspace_folder_routes_to_vscode(self):
        router = ActionRouter()
        action = AgentAction(type="open_folder", path="other_folder")
        with patch.object(router.vscode, "open_file", return_value=True) as mock_open:
            res = router.execute(action)
            self.assertTrue(res.success)
            self.assertIn("in VS Code", res.message)
            mock_open.assert_called_once()
            called_path = mock_open.call_args[0][0]
            self.assertEqual(called_path.resolve(), self.other_folder.resolve())

    def test_action_router_vscode_open_file(self):
        router = ActionRouter()
        action = AgentAction(type="vscode_open_file", path="deep/data.md")
        with patch.object(router.vscode, "open_file", return_value=True) as mock_open:
            res = router.execute(action)
            self.assertTrue(res.success)
            self.assertIn("Opened file 'data.md' in VS Code", res.message)
            mock_open.assert_called_once()
            called_path = mock_open.call_args[0][0]
            self.assertEqual(called_path.resolve(), self.data_file.resolve())

    def test_speech_normalizer_spaces_around_extension_dot(self):
        norm = SpeechNormalizer()
        self.assertEqual(norm.normalize_command("open main. py"), "open main.py")
        self.assertEqual(norm.normalize_command("open calc . py"), "open calc.py")
        self.assertEqual(norm.normalize_command("open main dot py"), "open main.py")
        self.assertEqual(norm.normalize_command("open notes dot txt"), "open notes.txt")

    def test_fast_router_folder_variations(self):
        fr = FastCommandRouter()
        p1 = fr.plan_for_command("open practical folder")
        self.assertIsNotNone(p1)
        self.assertEqual(p1.actions[0].type, "open_folder")
        self.assertEqual(p1.actions[0].path, "practical")

        p2 = fr.plan_for_command("open folder practical")
        self.assertIsNotNone(p2)
        self.assertEqual(p2.actions[0].type, "open_folder")
        self.assertEqual(p2.actions[0].path, "practical")

        p3 = fr.plan_for_command("open my file")
        self.assertIsNotNone(p3)
        self.assertEqual(p3.actions[0].type, "open_file")
        self.assertEqual(p3.actions[0].path, "my file")

    def test_action_router_open_app_catches_workspace_file(self):
        router = ActionRouter()
        # When user says "open script" which isn't a known app, it resolves to workspace script.py
        action = AgentAction(type="open_app", app="script")
        with patch.object(router.vscode, "open_file", return_value=True) as mock_open:
            res = router.execute(action)
            self.assertTrue(res.success)
            self.assertIn("Opened file 'script.py' in VS Code", res.message)
            mock_open.assert_called_once()
            called_path = mock_open.call_args[0][0]
            self.assertEqual(called_path.resolve(), self.script_file.resolve())

    def test_action_router_open_app_preserves_standard_apps(self):
        router = ActionRouter()
        action = AgentAction(type="open_app", app="notepad")
        with patch.object(router.apps, "open_or_activate", return_value="Opened Notepad.") as mock_app:
            with patch.object(router.vscode, "open_file") as mock_vscode:
                res = router.execute(action)
                self.assertTrue(res.success)
                mock_app.assert_called_once_with("notepad")
                mock_vscode.assert_not_called()

    def test_open_absolute_folder_in_vscode(self):
        fr = FastCommandRouter()
        cmd = f"open {self.subfolder} folder in vscode"
        plan = fr.plan_for_command(cmd)
        self.assertIsNotNone(plan)
        self.assertEqual(plan.actions[0].type, "vscode_open_file")
        self.assertEqual(Path(plan.actions[0].path).resolve(), self.subfolder.resolve())

        router = ActionRouter()
        with patch.object(router.vscode, "open_file", return_value=True) as mock_open:
            res = router.execute(plan.actions[0])
            self.assertTrue(res.success)
            self.assertIn("Opened folder 'subfolder' in VS Code", res.message)
            mock_open.assert_called_once()
            self.assertEqual(mock_open.call_args[0][0].resolve(), self.subfolder.resolve())

    def test_open_absolute_file_in_vscode(self):
        fr = FastCommandRouter()
        cmd = f"open {self.main_file} file in vscode"
        plan = fr.plan_for_command(cmd)
        self.assertIsNotNone(plan)
        self.assertEqual(plan.actions[0].type, "vscode_open_file")
        self.assertEqual(Path(plan.actions[0].path).resolve(), self.main_file.resolve())

        router = ActionRouter()
        with patch.object(router.vscode, "open_file", return_value=True) as mock_open:
            res = router.execute(plan.actions[0])
            self.assertTrue(res.success)
            self.assertIn("Opened file 'main.py' in VS Code", res.message)
            mock_open.assert_called_once()
            self.assertEqual(mock_open.call_args[0][0].resolve(), self.main_file.resolve())

    def test_spoken_path_folder_in_vscode(self):
        drive = self.subfolder.drive.replace(":", "")
        rest = " ".join(self.subfolder.parts[1:])
        spoken = f"{drive} {rest}"

        fr = FastCommandRouter()
        cmd = f"open {spoken} folder in vscode"
        plan = fr.plan_for_command(cmd)
        self.assertIsNotNone(plan)
        self.assertEqual(plan.actions[0].type, "vscode_open_file")
        self.assertEqual(plan.reply, "Opening subfolder in VS Code.")
        self.assertEqual(plan.actions[0].path, spoken)

        router = ActionRouter()
        with patch.object(router.vscode, "open_file", return_value=True) as mock_open:
            res = router.execute(plan.actions[0])
            self.assertTrue(res.success)
            self.assertIn("Opened folder 'subfolder' in VS Code", res.message)
            mock_open.assert_called_once()
            self.assertEqual(mock_open.call_args[0][0].resolve(), self.subfolder.resolve())

    def test_spoken_path_file_in_vscode(self):
        drive = self.main_file.drive.replace(":", "")
        rest = " ".join(self.main_file.parts[1:])
        spoken = f"{drive} {rest}"

        fr = FastCommandRouter()
        cmd = f"open {spoken} in vscode"
        plan = fr.plan_for_command(cmd)
        self.assertIsNotNone(plan)
        self.assertEqual(plan.actions[0].type, "vscode_open_file")
        self.assertEqual(plan.reply, "Opening main.py in VS Code.")
        self.assertEqual(plan.actions[0].path, spoken)

        router = ActionRouter()
        with patch.object(router.vscode, "open_file", return_value=True) as mock_open:
            res = router.execute(plan.actions[0])
            self.assertTrue(res.success)
            self.assertIn("Opened file 'main.py' in VS Code", res.message)
            mock_open.assert_called_once()
            self.assertEqual(mock_open.call_args[0][0].resolve(), self.main_file.resolve())

    def test_user_spoken_path_practice_python(self):
        target = Path("C:/Users/amrat/Desktop/practice/python")
        if target.exists():
            fr = FastCommandRouter()
            cmd = "open c users amrat desktop practice python folder in vscode"
            plan = fr.plan_for_command(cmd)
            self.assertIsNotNone(plan)
            self.assertEqual(plan.actions[0].type, "vscode_open_file")
            self.assertEqual(plan.reply, "Opening python in VS Code.")
            self.assertEqual(plan.actions[0].path, "c users amrat desktop practice python")

            router = ActionRouter()
            with patch.object(router.vscode, "open_file", return_value=True) as mock_open:
                res = router.execute(plan.actions[0])
                self.assertTrue(res.success)
                self.assertIn("Opened folder 'python' in VS Code", res.message)
                mock_open.assert_called_once()
                self.assertEqual(mock_open.call_args[0][0].resolve(), target.resolve())

    def test_speech_normalizer_amrat_mishearings(self):
        norm = SpeechNormalizer()
        self.assertEqual(
            norm.normalize_command("open c users android desktop practice python folder in vscode"),
            "open c users amrat desktop practice python folder in vscode"
        )
        self.assertEqual(
            norm.normalize_command("open c users camera desktop practice python folder in vscode"),
            "open c users amrat desktop practice python folder in vscode"
        )
        self.assertEqual(
            norm.normalize_command("open c users amrit desktop practice python folder in vscode"),
            "open c users amrat desktop practice python folder in vscode"
        )
        self.assertEqual(
            norm.normalize_command("open c users am rat desktop practice python folder in vscode"),
            "open c users amrat desktop practice python folder in vscode"
        )
        self.assertEqual(
            norm.normalize_command("open android.py in vscode"),
            "open amrat.py in vscode"
        )
        self.assertEqual(
            norm.normalize_command("open camera.py in vscode"),
            "open amrat.py in vscode"
        )
        self.assertEqual(
            norm.normalize_command("open amrit.py in vscode"),
            "open amrat.py in vscode"
        )
        self.assertEqual(
            norm.normalize_command("open android in vscode"),
            "open amrat in vscode"
        )
        self.assertEqual(
            norm.normalize_command("open camera in vscode"),
            "open amrat in vscode"
        )
        # Ensure standard "open camera" still opens the camera app!
        self.assertEqual(norm.normalize_command("open camera"), "open camera")

    def test_vscode_find_in_workspace_amrat_aliases(self):
        amrat_file = self.subfolder / "amrat.py"
        amrat_file.write_text("print('amrat')", encoding="utf-8")
        try:
            self.assertEqual(self.adapter.find_in_workspace("android.py"), amrat_file)
            self.assertEqual(self.adapter.find_in_workspace("camera.py"), amrat_file)
            self.assertEqual(self.adapter.find_in_workspace("amrit.py"), amrat_file)
            self.assertEqual(self.adapter.find_in_workspace("android"), amrat_file)
            self.assertEqual(self.adapter.find_in_workspace("camera"), amrat_file)
        finally:
            if amrat_file.exists():
                amrat_file.unlink()

    def test_spoken_path_with_misheard_username(self):
        target = Path("C:/Users/amrat/Desktop/practice/python")
        if target.exists():
            for spoken in [
                "c users android desktop practice python",
                "c users camera desktop practice python",
                "c users amrit desktop practice python",
                "c users am rat desktop practice python",
                "users android desktop practice python",
                "users camera desktop practice python",
            ]:
                resolved = WindowsPathResolver.resolve_spoken_path(spoken)
                self.assertIsNotNone(resolved, f"Failed for {spoken}")
                self.assertEqual(resolved.resolve(), target.resolve(), f"Mismatch for {spoken}")


if __name__ == "__main__":
    unittest.main()
