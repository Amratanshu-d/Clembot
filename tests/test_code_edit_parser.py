"""
tests/test_code_edit_parser.py
Tests for the CodeEditParser — verifies that voice commands are parsed
into the correct structured tokens across a comprehensive set of paraphrases,
rephrasings, rewordings, and restatements.
"""
import unittest
from app.editor.code_edit_parser import parse_voice_edit, _parse_line_number
from app.ai.local_heuristic import LocalHeuristicPlanner
from app.core.models import ScreenContext


class TestCodeEditParser(unittest.TestCase):

    # =========================================================================
    # 1. PARAPHRASING: Standard & Colloquial In-Line Replacement
    # =========================================================================

    def test_replace_in_line_user_reported_case(self):
        """User case: 'in line 36 replace with from what' (replace 'with' with 'what')."""
        r = parse_voice_edit("in line 36 replace with from what")
        self.assertIsNotNone(r)
        self.assertEqual(r.token, "REPLACE_IN_LINE:36:with::what")
        self.assertEqual(r.line_number, 36)

    def test_replace_in_line_user_reported_without_in(self):
        """Paraphrase without leading preposition: 'line 36 replace with from what'."""
        r = parse_voice_edit("line 36 replace with from what")
        self.assertIsNotNone(r)
        self.assertEqual(r.token, "REPLACE_IN_LINE:36:with::what")
        self.assertEqual(r.line_number, 36)

    def test_replace_in_line_compound_inline(self):
        """User case: 'inline 43 replace I with J'."""
        r = parse_voice_edit("inline 43 replace I with J")
        self.assertIsNotNone(r)
        self.assertEqual(r.token, "REPLACE_IN_LINE:43:I::J")
        self.assertEqual(r.line_number, 43)

    def test_replace_in_line_line_without_prep(self):
        """Paraphrase: 'line 43 replace I with J'."""
        r = parse_voice_edit("line 43 replace I with J")
        self.assertIsNotNone(r)
        self.assertEqual(r.token, "REPLACE_IN_LINE:43:I::J")
        self.assertEqual(r.line_number, 43)

    def test_replace_in_line_basic_in(self):
        r = parse_voice_edit("in line 6 replace char with int")
        self.assertIsNotNone(r)
        self.assertEqual(r.token, "REPLACE_IN_LINE:6:char::int")
        self.assertEqual(r.line_number, 6)

    def test_replace_in_line_on(self):
        r = parse_voice_edit("on line 10 replace hello with world")
        self.assertIsNotNone(r)
        self.assertEqual(r.token, "REPLACE_IN_LINE:10:hello::world")

    def test_replace_in_line_at(self):
        r = parse_voice_edit("at line 36 swap with with what")
        self.assertIsNotNone(r)
        self.assertEqual(r.token, "REPLACE_IN_LINE:36:with::what")

    def test_replace_in_line_change_to(self):
        r = parse_voice_edit("in line 3 change x to counter")
        self.assertIsNotNone(r)
        self.assertEqual(r.token, "REPLACE_IN_LINE:3:x::counter")

    def test_replace_in_line_substitute_by(self):
        r = parse_voice_edit("in line 36 substitute with by what")
        self.assertIsNotNone(r)
        self.assertEqual(r.token, "REPLACE_IN_LINE:36:with::what")

    def test_replace_in_line_update_to(self):
        r = parse_voice_edit("line 36 update foo to bar")
        self.assertIsNotNone(r)
        self.assertEqual(r.token, "REPLACE_IN_LINE:36:foo::bar")

    def test_replace_in_line_modify_to(self):
        r = parse_voice_edit("on line 12 modify old_val to new_val")
        self.assertIsNotNone(r)
        self.assertEqual(r.token, "REPLACE_IN_LINE:12:old_val::new_val")

    def test_replace_keyword_qualifier_stripped(self):
        r = parse_voice_edit("in line 6 replace the char keyword with int")
        self.assertIsNotNone(r)
        self.assertEqual(r.token, "REPLACE_IN_LINE:6:char::int")

    def test_replace_variable_qualifier_stripped(self):
        r = parse_voice_edit("on line 15 replace the variable total with sum_amount")
        self.assertIsNotNone(r)
        self.assertEqual(r.token, "REPLACE_IN_LINE:15:total::sum_amount")

    # =========================================================================
    # 2. REPHRASING: Inverted Orders & Connectors
    # =========================================================================

    def test_rephrasing_post_position_line(self):
        """Rephrasing: line reference placed at the end."""
        r = parse_voice_edit("replace char with int in line 6")
        self.assertIsNotNone(r)
        self.assertEqual(r.token, "REPLACE_IN_LINE:6:char::int")

    def test_rephrasing_post_position_on_line(self):
        r = parse_voice_edit("replace I with J on line 43")
        self.assertIsNotNone(r)
        self.assertEqual(r.token, "REPLACE_IN_LINE:43:I::J")

    def test_rephrasing_post_position_by_connector(self):
        r = parse_voice_edit("replace I by J in line 43")
        self.assertIsNotNone(r)
        self.assertEqual(r.token, "REPLACE_IN_LINE:43:I::J")

    def test_rephrasing_post_position_from_connector(self):
        r = parse_voice_edit("replace I from J in line 43")
        self.assertIsNotNone(r)
        self.assertEqual(r.token, "REPLACE_IN_LINE:43:I::J")

    def test_rephrasing_post_position_swap(self):
        r = parse_voice_edit("swap foo with bar on line 10")
        self.assertIsNotNone(r)
        self.assertEqual(r.token, "REPLACE_IN_LINE:10:foo::bar")

    def test_rephrasing_post_position_change(self):
        r = parse_voice_edit("change foo to bar in line 12")
        self.assertIsNotNone(r)
        self.assertEqual(r.token, "REPLACE_IN_LINE:12:foo::bar")

    def test_rephrasing_replace_from_to(self):
        """Rephrasing: 'replace from <old> to <new>'."""
        r = parse_voice_edit("in line 36 replace from with to what")
        self.assertIsNotNone(r)
        self.assertEqual(r.token, "REPLACE_IN_LINE:36:with::what")

    def test_rephrasing_replace_with_from(self):
        """Rephrasing: 'replace with <new> from <old>'."""
        r = parse_voice_edit("in line 36 replace with what from with")
        self.assertIsNotNone(r)
        self.assertEqual(r.token, "REPLACE_IN_LINE:36:with::what")

    def test_for_line_replace_word(self):
        r = parse_voice_edit("for line 9 replace names with items")
        self.assertIsNotNone(r)
        self.assertEqual(r.token, "REPLACE_IN_LINE:9:names::items")

    # =========================================================================
    # 3. REWORDING: Whole-Line Overwrites & Substitutions
    # =========================================================================

    def test_rewording_in_line_replace_with(self):
        """Rewording: 'in line 36 replace with x = 10'."""
        r = parse_voice_edit("in line 36 replace with x = 10")
        self.assertIsNotNone(r)
        self.assertEqual(r.token, "REPLACE_LINE:36::x = 10")

    def test_rewording_line_replace_with(self):
        r = parse_voice_edit("line 36 replace with x = 10")
        self.assertIsNotNone(r)
        self.assertEqual(r.token, "REPLACE_LINE:36::x = 10")

    def test_rewording_inline_replace_with(self):
        r = parse_voice_edit("inline 36 replace with x = 10")
        self.assertIsNotNone(r)
        self.assertEqual(r.token, "REPLACE_LINE:36::x = 10")

    def test_rewording_rewrite_as(self):
        r = parse_voice_edit("line 36 rewrite as x = 10")
        self.assertIsNotNone(r)
        self.assertEqual(r.token, "REPLACE_LINE:36::x = 10")

    def test_rewording_overwrite_with(self):
        r = parse_voice_edit("line 36 overwrite with x = 10")
        self.assertIsNotNone(r)
        self.assertEqual(r.token, "REPLACE_LINE:36::x = 10")

    def test_rewording_set_to(self):
        r = parse_voice_edit("line 36 set to x = 10")
        self.assertIsNotNone(r)
        self.assertEqual(r.token, "REPLACE_LINE:36::x = 10")

    def test_rewording_put_on_line(self):
        r = parse_voice_edit("put x = 10 on line 36")
        self.assertIsNotNone(r)
        self.assertEqual(r.token, "REPLACE_LINE:36::x = 10")

    def test_rewording_put_in_line(self):
        r = parse_voice_edit("put return None in line 50")
        self.assertIsNotNone(r)
        self.assertEqual(r.token, "REPLACE_LINE:50::return None")

    def test_rewording_make_line(self):
        r = parse_voice_edit("line 36 make it x = 10")
        self.assertIsNotNone(r)
        self.assertEqual(r.token, "REPLACE_LINE:36::x = 10")

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

    # =========================================================================
    # 4. RESTATING: Spoken Number Names & Compound Digits
    # =========================================================================

    def test_restating_compound_number_thirty_six(self):
        """Restating numbers: 'thirty six' -> 36."""
        r = parse_voice_edit("in line thirty six replace with from what")
        self.assertIsNotNone(r)
        self.assertEqual(r.token, "REPLACE_IN_LINE:36:with::what")
        self.assertEqual(r.line_number, 36)

    def test_restating_hyphenated_number_forty_three(self):
        """Restating numbers: 'forty-three' -> 43."""
        r = parse_voice_edit("inline forty-three replace I with J")
        self.assertIsNotNone(r)
        self.assertEqual(r.token, "REPLACE_IN_LINE:43:I::J")
        self.assertEqual(r.line_number, 43)

    def test_restating_delete_compound_number(self):
        r = parse_voice_edit("delete line twenty one")
        self.assertIsNotNone(r)
        self.assertEqual(r.token, "DELETE_LINE:21")

    def test_restating_parse_line_number_helper(self):
        self.assertEqual(_parse_line_number("36"), 36)
        self.assertEqual(_parse_line_number("thirty six"), 36)
        self.assertEqual(_parse_line_number("thirty-six"), 36)
        self.assertEqual(_parse_line_number("forty three"), 43)
        self.assertEqual(_parse_line_number("line 43"), 43)
        self.assertEqual(_parse_line_number("inline 43"), 43)
        self.assertEqual(_parse_line_number("one hundred"), 100)
        self.assertEqual(_parse_line_number("one hundred and five"), 105)

    # =========================================================================
    # 5. DELETION, INSERTION, COMMENTING RESTATEMENTS
    # =========================================================================

    def test_delete_line(self):
        r = parse_voice_edit("delete line 10")
        self.assertIsNotNone(r)
        self.assertEqual(r.token, "DELETE_LINE:10")

    def test_remove_line(self):
        r = parse_voice_edit("remove line 5")
        self.assertIsNotNone(r)
        self.assertEqual(r.token, "DELETE_LINE:5")

    def test_drop_line_paraphrase(self):
        r = parse_voice_edit("drop line 36")
        self.assertIsNotNone(r)
        self.assertEqual(r.token, "DELETE_LINE:36")

    def test_in_line_delete_restatement(self):
        r = parse_voice_edit("in line 36 delete")
        self.assertIsNotNone(r)
        self.assertEqual(r.token, "DELETE_LINE:36")

    def test_delete_lines_range(self):
        r = parse_voice_edit("delete lines 5 to 8")
        self.assertIsNotNone(r)
        self.assertEqual(r.token, "DELETE_LINES:5:8")

    def test_delete_lines_through(self):
        r = parse_voice_edit("delete lines 3 through 6")
        self.assertIsNotNone(r)
        self.assertEqual(r.token, "DELETE_LINES:3:6")

    def test_insert_after(self):
        r = parse_voice_edit("insert print hello after line 5")
        self.assertIsNotNone(r)
        self.assertEqual(r.token, "INSERT_AFTER:5::print hello")

    def test_insert_after_inverted(self):
        r = parse_voice_edit("after line 5 insert print hello")
        self.assertIsNotNone(r)
        self.assertEqual(r.token, "INSERT_AFTER:5::print hello")

    def test_insert_before(self):
        r = parse_voice_edit("insert x = 0 before line 3")
        self.assertIsNotNone(r)
        self.assertEqual(r.token, "INSERT_BEFORE:3::x = 0")

    def test_insert_before_inverted(self):
        r = parse_voice_edit("before line 3 add x = 0")
        self.assertIsNotNone(r)
        self.assertEqual(r.token, "INSERT_BEFORE:3::x = 0")

    def test_comment_line(self):
        r = parse_voice_edit("comment out line 7")
        self.assertIsNotNone(r)
        self.assertEqual(r.token, "COMMENT_LINE:7")

    def test_comment_line_without_out(self):
        r = parse_voice_edit("comment line 7")
        self.assertIsNotNone(r)
        self.assertEqual(r.token, "COMMENT_LINE:7")

    def test_in_line_comment(self):
        r = parse_voice_edit("in line 7 comment out")
        self.assertIsNotNone(r)
        self.assertEqual(r.token, "COMMENT_LINE:7")

    def test_uncomment_line(self):
        r = parse_voice_edit("uncomment line 7")
        self.assertIsNotNone(r)
        self.assertEqual(r.token, "UNCOMMENT_LINE:7")

    def test_in_line_uncomment(self):
        r = parse_voice_edit("in line 7 uncomment")
        self.assertIsNotNone(r)
        self.assertEqual(r.token, "UNCOMMENT_LINE:7")

    def test_rename_function(self):
        r = parse_voice_edit("rename function foo to bar")
        self.assertIsNotNone(r)
        self.assertEqual(r.token, "RENAME_FUNC:foo:bar")

    def test_add_try_except(self):
        r = parse_voice_edit("add try except at line 12")
        self.assertIsNotNone(r)
        self.assertEqual(r.token, "ADD_TRY_EXCEPT:12")

    def test_add_try_except_default_line(self):
        r = parse_voice_edit("add a try except block")
        self.assertIsNotNone(r)
        self.assertTrue(r.token.startswith("ADD_TRY_EXCEPT"))

    # =========================================================================
    # 6. NEGATIVE & NO-MATCH CASES
    # =========================================================================

    def test_no_match_open_vscode(self):
        r = parse_voice_edit("open VS Code")
        self.assertIsNone(r)

    def test_no_match_general_question(self):
        r = parse_voice_edit("what is machine learning")
        self.assertIsNone(r)


class TestLocalHeuristicCodeGuard(unittest.TestCase):
    """Verifies that unparsed or partial code edits NEVER fall back to Google Web Search."""

    def setUp(self):
        self.planner = LocalHeuristicPlanner()
        self.context = ScreenContext()

    def test_incomplete_line_replace_does_not_google_search(self):
        """User input cut off: 'in line 36 replace with' must not trigger Google search."""
        plan = self.planner.plan("in line 36 replace with", self.context)
        self.assertIsNotNone(plan)
        # Verify no web_search actions are generated!
        self.assertEqual(len(plan.actions), 0)
        self.assertIn("code edit command", plan.reply.lower())
        self.assertIn("36", plan.reply)

    def test_incomplete_delete_line_does_not_google_search(self):
        plan = self.planner.plan("delete line", self.context)
        self.assertIsNotNone(plan)
        self.assertEqual(len(plan.actions), 0)
        self.assertIn("code edit command", plan.reply.lower())

    def test_general_query_still_falls_back_to_search(self):
        """Ensure genuine general questions without code markers still search."""
        plan = self.planner.plan("what is the weather today", self.context)
        self.assertIsNotNone(plan)
        self.assertEqual(len(plan.actions), 1)
        self.assertEqual(plan.actions[0].type, "web_search")


if __name__ == "__main__":
    unittest.main()
