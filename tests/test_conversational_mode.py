import unittest
from unittest.mock import MagicMock, patch
from app.ai.language_detector import LanguageDetector
from app.commands.router import ActionRouter
from app.core.models import AgentAction, AgentPlan
from app.core.orchestrator import AssistantOrchestrator


class TestConversationalMode(unittest.TestCase):
    def setUp(self):
        self.detector = LanguageDetector()
        self.router = ActionRouter()

    def test_hinglish_detection(self):
        self.assertTrue(self.detector.is_hinglish("bolate kya"))
        self.assertTrue(self.detector.is_hinglish("kaise ho"))
        self.assertTrue(self.detector.is_hinglish("kya kar rahe ho"))
        self.assertTrue(self.detector.is_hinglish("namaste clembot"))
        self.assertTrue(self.detector.is_hinglish("batao distance"))

        # Pure English desktop commands should NOT be Hinglish
        self.assertFalse(self.detector.is_hinglish("open downloads"))
        self.assertFalse(self.detector.is_hinglish("create folder projects"))
        self.assertFalse(self.detector.is_hinglish("minimize window"))

    def test_question_intent_detection(self):
        self.assertTrue(self.detector.is_conversational_question("tell distance from satna to jabalpur"))
        self.assertTrue(self.detector.is_conversational_question("what is the capital of France?"))
        self.assertTrue(self.detector.is_conversational_question("how far is the moon"))
        self.assertTrue(self.detector.is_conversational_question("can you explain quantum computing"))

    def test_answer_question_action_in_router(self):
        action = AgentAction(type="answer_question", text="The distance is 200 kilometers.")
        res = self.router.execute(action)
        self.assertTrue(res.success)
        self.assertEqual(res.message, "The distance is 200 kilometers.")

    def test_orchestrator_routes_hinglish_to_ai_provider(self):
        orch = AssistantOrchestrator()
        mock_plan = AgentPlan(reply="Main theek hoon! Aap batayein?", actions=[])

        with patch.object(orch.ai_provider, "plan", return_value=mock_plan) as mock_plan_call:
            with patch.object(orch, "has_active_llm", return_value=True):
                orch.process_command("bolate kya")
                mock_plan_call.assert_called_once()
                args, _ = mock_plan_call.call_args
                self.assertIn("bolate kya", args[0])


if __name__ == "__main__":
    unittest.main()
