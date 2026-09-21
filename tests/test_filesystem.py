import shutil
import tempfile
import unittest
from pathlib import Path

from app.filesystem.service import FileSystemService


class TestFileSystemService(unittest.TestCase):
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp(prefix="clembot_test_fs_"))
        self.fs = FileSystemService()

    def tearDown(self):
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_create_and_read_file(self):
        file_path = self.temp_dir / "notes.txt"
        res = self.fs.create_file(file_path, "Hello Clembot!", base_context=self.temp_dir)
        self.assertTrue(file_path.is_file())
        self.assertEqual(file_path.read_text(encoding="utf-8"), "Hello Clembot!")
        self.assertIn("notes.txt", res)

    def test_create_folder(self):
        folder_path = self.temp_dir / "Projects"
        res = self.fs.create_folder(folder_path, base_context=self.temp_dir)
        self.assertTrue(folder_path.is_dir())
        self.assertIn("Projects", res)

    def test_rename_file(self):
        src = self.temp_dir / "old_name.txt"
        src.write_text("sample content", encoding="utf-8")
        self.fs.rename_item(src, "new_name.txt")
        self.assertFalse(src.exists())
        self.assertTrue((self.temp_dir / "new_name.txt").is_file())

    def test_copy_and_move_file(self):
        src = self.temp_dir / "data.txt"
        src.write_text("data", encoding="utf-8")
        sub = self.temp_dir / "subdir"
        sub.mkdir()

        # Copy
        self.fs.copy_item(src, sub)
        self.assertTrue(src.exists())
        self.assertTrue((sub / "data.txt").exists())

        # Move
        dest_move = self.temp_dir / "moved.txt"
        self.fs.move_item(src, dest_move)
        self.assertFalse(src.exists())
        self.assertTrue(dest_move.exists())

    def test_list_directory(self):
        (self.temp_dir / "file1.txt").write_text("a")
        (self.temp_dir / "file2.txt").write_text("b")
        (self.temp_dir / "folder1").mkdir()

        summary, data = self.fs.list_directory(self.temp_dir)
        self.assertIn("2 files", summary)
        self.assertIn("1 folder", summary)
        self.assertEqual(len(data["files"]), 2)
        self.assertEqual(len(data["folders"]), 1)

    def test_count_items_in_directory(self):
        (self.temp_dir / "f1.txt").write_text("a")
        sub = self.temp_dir / "sub"
        sub.mkdir()
        (sub / "f2.txt").write_text("b")

        count = self.fs.count_items_in_directory(self.temp_dir)
        self.assertEqual(count, 3)  # 2 files + 1 dir


if __name__ == "__main__":
    unittest.main()
