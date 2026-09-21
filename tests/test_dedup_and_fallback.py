import unittest
import time
from unittest.mock import MagicMock
from app.ai.local_heuristic import LocalHeuristicPlanner
from app.core.models import AssistantState, ScreenContext
from app.core.orchestrator import AssistantOrchestrator


class TestDedupAndFallback(unittest.TestCase):
    def test_local_heuristic_web_search_fallback(self):
        planner = LocalHeuristicPlanner()
        ctx = ScreenContext()
        # Any query that cannot be performed locally must fall back to web search
        plan = planner.plan("tell distance from satna to jabalpur", ctx)
        self.assertIsNotNone(plan)
        self.assertEqual(len(plan.actions), 1)
        self.assertEqual(plan.actions[0].type, "web_search")
        self.assertEqual(plan.actions[0].scope, "google")

    def test_orchestrator_dedup(self):
        orch = AssistantOrchestrator()
        orch.set_state(AssistantState.LISTENING)

        mock_process = MagicMock()
        orch.process_command = mock_process

        # First call executes
        orch.handle_user_input("open vscode")
        self.assertEqual(mock_process.call_count, 1)

        # Immediate duplicate within 1.5s is ignored
        orch.handle_user_input("open vscode")
        self.assertEqual(mock_process.call_count, 1)

        # Different command executes
        orch.handle_user_input("open downloads")
        self.assertEqual(mock_process.call_count, 2)


if __name__ == "__main__":
    unittest.main()
