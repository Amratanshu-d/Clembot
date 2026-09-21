from abc import ABC, abstractmethod
from typing import Optional
from app.core.models import AgentPlan, ScreenContext


class AIProvider(ABC):
    """Abstract interface for AI planning and natural language command understanding."""

    @abstractmethod
    def plan(self, command: str, context: ScreenContext) -> AgentPlan:
        """Translates a natural language command and desktop context into a structured AgentPlan."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Returns True if the provider is configured and reachable."""
        pass
