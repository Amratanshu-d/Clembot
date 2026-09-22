import unittest
from pathlib import Path

from app.ai.prompt_builder import AIPromptBuilder
from app.core.models import AgentAction, AgentPlan, ScreenContext
from app.core.orchestrator import AssistantOrchestrator
from app.memory.conversation import ConversationalMemory


class TestConversationalCoding(unittest.TestCase):
    def setUp(self):
        self.memory = ConversationalMemory()
        self.builder = AIPromptBuilder()

    def test_undo_reference_resolution(self):
        # English phrases
        self.assertEqual(self.memory.resolve_contextual_references("undo that"), "undo")
        self.assertEqual(self.memory.resolve_contextual_references("change it back"), "undo")
        self.assertEqual(self.memory.resolve_contextual_references("revert that"), "undo")
        # Hinglish phrases
        self.assertEqual(self.memory.resolve_contextual_references("jo abhi change kiya tha usko undo karo"), "undo")
        self.assertEqual(self.memory.resolve_contextual_references("pehle jaisa kar do"), "undo")

    def test_symbol_reference_resolution(self):
        file_path = Path("F:/projects/app.py")
        self.memory.record_code_patch(
            file_path=file_path,
            explanation="Added error handling to process_data",
            symbol_name="process_data"
        )

        resolved = self.memory.resolve_contextual_references("make that function async")
        self.assertIn("process_data", resolved)

    def test_multi_file_contextual_resolution(self):
        file1 = Path("F:/projects/models.py")
        file2 = Path("F:/projects/views.py")

        self.memory.record_code_patch(file1, "Added User model", symbol_name="User")
        self.memory.record_code_patch(file2, "Updated login view", symbol_name="login")

        # "this file" / "same file" resolves to most recent (file2)
        resolved_same = self.memory.resolve_contextual_references("add logout in this file")
        self.assertIn("views.py", resolved_same)

        # "the other file" resolves to file1
        resolved_other = self.memory.resolve_contextual_references("open the other file")
        self.assertIn("models.py", resolved_other)

    def test_memory_context_dictionary(self):
        file_path = Path("F:/projects/main.py")
        self.memory.record_code_patch(file_path, "Refactored startup", symbol_name="startup")
        self.memory.record_error("TypeError: cannot unpack non-iterable NoneType object")

        ctx_dict = self.memory.get_memory_context_dict()
        self.assertIn("main.py", ctx_dict["last_file"])
        self.assertEqual(ctx_dict["last_symbol"], "startup")
        self.assertIn("Refactored startup", ctx_dict["last_patch_summary"])
        self.assertIn("TypeError", ctx_dict["last_error"])

    def test_prompt_builder_system_instruction(self):
        instr = self.builder.build_system_instruction()
        self.assertIn("vscode_patch", instr)
        self.assertIn("INTENT CLASSIFICATION", instr)
        self.assertIn("code_mod", instr)
        self.assertIn("HINGLISH EXAMPLES", instr)
        self.assertIn("VOICE / TTS OUTPUT RULES", instr)

    def test_prompt_builder_user_prompt_rich_context(self):
        ctx = ScreenContext(
            vscode_file="F:/app/server.py",
            vscode_line=45,
            focused_code_snippet="45: def handle_request():\n46:     pass",
            last_modified_symbol="handle_request",
            last_edit_summary="Added handle_request placeholder"
        )

        user_prompt = self.builder.build_user_prompt("make it async", ctx)
        self.assertIn("server.py", user_prompt)
        self.assertIn("Line: 45", user_prompt)
        self.assertIn("handle_request", user_prompt)
        self.assertIn("def handle_request():", user_prompt)
        self.assertIn("make it async", user_prompt)

    def test_prompt_builder_validates_vscode_patch_schema(self):
        raw_json = '''{
            "reply": "I changed the timeout to 30 seconds.",
            "intent": "code_mod",
            "actions": [
                {
                    "type": "vscode_patch",
                    "path": "config.py",
                    "target_code": "TIMEOUT = 10",
                    "replacement_code": "TIMEOUT = 30",
                    "patch_action": "replace",
                    "instruction": "Update timeout constant"
                }
            ]
        }'''

        plan = self.builder.parse_and_validate(raw_json)
        self.assertEqual(plan.intent, "code_mod")
        self.assertEqual(len(plan.actions), 1)
        action = plan.actions[0]
        self.assertEqual(action.type, "vscode_patch")
        self.assertEqual(action.target_code, "TIMEOUT = 10")
        self.assertEqual(action.replacement_code, "TIMEOUT = 30")

    def test_tts_markdown_stripping(self):
        markdown_text = (
            "Here is the result:\n"
            "# Summary\n"
            "- Step 1: Use `run_code()` function\n"
            "- Step 2: Check **bold** and *italic* notes\n"
            "```python\nprint('code')\n```\n"
            "Done!"
        )
        clean = AssistantOrchestrator._strip_markdown_for_voice(markdown_text)
        self.assertNotIn("```", clean)
        self.assertNotIn("**", clean)
        self.assertNotIn("`run_code()`", clean)
        self.assertIn("run_code()", clean)
        self.assertNotIn("# Summary", clean)
        self.assertIn("Summary", clean)


if __name__ == "__main__":
    unittest.main()
