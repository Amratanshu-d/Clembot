"""
tests/test_code_edit_parser.py
Tests for the CodeEditParser — verifies that voice commands are parsed
into the correct structured tokens.
"""
import unittest
from app.editor.code_edit_parser import parse_voice_edit


class TestCodeEditParser(unittest.TestCase):

    # ----- REPLACE IN LINE -----
    def test_replace_in_line_basic(self):
        r = parse_voice_edit("in line 6 replace char with int")
        self.assertIsNotNone(r)
        self.assertEqual(r.token, "REPLACE_IN_LINE:6:char::int")
        self.assertEqual(r.line_number, 6)

    def test_replace_in_line_on(self):
        r = parse_voice_edit("on line 10 replace hello with world")
        self.assertIsNotNone(r)
        self.assertTrue(r.token.startswith("REPLACE_IN_LINE:10:hello::world"))

    def test_replace_in_line_change_to(self):
        r = parse_voice_edit("in line 3 change x to counter")
        self.assertIsNotNone(r)
        self.assertEqual(r.token, "REPLACE_IN_LINE:3:x::counter")

    def test_replace_in_line_reverse_order(self):
        r = parse_voice_edit("replace char with int in line 6")
        self.assertIsNotNone(r)
        self.assertEqual(r.token, "REPLACE_IN_LINE:6:char::int")

    def test_replace_keyword_qualifier_stripped(self):
        r = parse_voice_edit("in line 6 replace the char keyword with int")
        self.assertIsNotNone(r)
        self.assertEqual(r.token, "REPLACE_IN_LINE:6:char::int")

    # ----- REPLACE ENTIRE LINE -----
    def test_replace_entire_line(self):
        r = parse_voice_edit("replace line 4 with x = 0")
        self.assertIsNotNone(r)
        self.assertEqual(r.token, "REPLACE_LINE:4::x = 0")

    def test_replace_whole_line(self):
        r = parse_voice_edit("replace entire line 7 with return None")
        self.assertIsNotNone(r)
        self.assertEqual(r.token, "REPLACE_LINE:7::return None")

    def test_for_line_replace_content(self):
        r = parse_voice_edit("for line 9 change the content to print(hello)")
        self.assertIsNotNone(r)
        self.assertEqual(r.token, "REPLACE_LINE:9::print(hello)")

    def test_change_the_content_in_line(self):
        r = parse_voice_edit("change the content in line 9 to print(names)")
        self.assertIsNotNone(r)
        self.assertEqual(r.token, "REPLACE_LINE:9::print(names)")

    def test_change_line_to(self):
        r = parse_voice_edit("change line 9 to for item in names:")
        self.assertIsNotNone(r)
        self.assertEqual(r.token, "REPLACE_LINE:9::for item in names:")

    def test_for_line_replace_word(self):
        r = parse_voice_edit("for line 9 replace names with items")
        self.assertIsNotNone(r)
        self.assertEqual(r.token, "REPLACE_IN_LINE:9:names::items")

    # ----- DELETE LINE -----
    def test_delete_line(self):
        r = parse_voice_edit("delete line 10")
        self.assertIsNotNone(r)
        self.assertEqual(r.token, "DELETE_LINE:10")

    def test_remove_line(self):
        r = parse_voice_edit("remove line 5")
        self.assertIsNotNone(r)
        self.assertEqual(r.token, "DELETE_LINE:5")

    def test_delete_lines_range(self):
        r = parse_voice_edit("delete lines 5 to 8")
        self.assertIsNotNone(r)
        self.assertEqual(r.token, "DELETE_LINES:5:8")

    def test_delete_lines_through(self):
        r = parse_voice_edit("delete lines 3 through 6")
        self.assertIsNotNone(r)
        self.assertEqual(r.token, "DELETE_LINES:3:6")

    # ----- INSERT -----
    def test_insert_after(self):
        r = parse_voice_edit("insert print hello after line 5")
        self.assertIsNotNone(r)
        self.assertTrue(r.token.startswith("INSERT_AFTER:5::"))
        self.assertIn("print hello", r.token)

    def test_insert_before(self):
        r = parse_voice_edit("insert x = 0 before line 3")
        self.assertIsNotNone(r)
        self.assertTrue(r.token.startswith("INSERT_BEFORE:3::"))
        self.assertIn("x = 0", r.token)

    # ----- COMMENT -----
    def test_comment_line(self):
        r = parse_voice_edit("comment out line 7")
        self.assertIsNotNone(r)
        self.assertEqual(r.token, "COMMENT_LINE:7")

    def test_uncomment_line(self):
        r = parse_voice_edit("uncomment line 7")
        self.assertIsNotNone(r)
        self.assertEqual(r.token, "UNCOMMENT_LINE:7")

    # ----- RENAME FUNCTION -----
    def test_rename_function(self):
        r = parse_voice_edit("rename function foo to bar")
        self.assertIsNotNone(r)
        self.assertEqual(r.token, "RENAME_FUNC:foo:bar")

    # ----- TRY EXCEPT -----
    def test_add_try_except(self):
        r = parse_voice_edit("add try except at line 12")
        self.assertIsNotNone(r)
        self.assertEqual(r.token, "ADD_TRY_EXCEPT:12")

    def test_add_try_except_default_line(self):
        r = parse_voice_edit("add a try except block")
        self.assertIsNotNone(r)
        self.assertTrue(r.token.startswith("ADD_TRY_EXCEPT"))

    # ----- NO MATCH -----
    def test_no_match_open_vscode(self):
        # "open VS Code" is not a code edit command
        r = parse_voice_edit("open VS Code")
        self.assertIsNone(r)

    def test_no_match_general_question(self):
        r = parse_voice_edit("what is machine learning")
        self.assertIsNone(r)


if __name__ == "__main__":
    unittest.main()
