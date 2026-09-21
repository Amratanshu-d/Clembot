from app.ai.base import AIProvider
from app.ai.gemini_provider import GeminiProvider
from app.ai.local_heuristic import LocalHeuristicPlanner
from app.ai.ollama_provider import OllamaProvider
from app.ai.openai_provider import OpenAIProvider
from app.config.settings import settings
from app.logging.logger import logger


class AIProviderFactory:
    """Factory creating the appropriate AI provider based on configuration."""

    @staticmethod
    def get_provider(provider_name: str = None) -> AIProvider:
        name = (provider_name or settings.default_ai_provider).lower().strip()

        if name == "gemini":
            provider = GeminiProvider()
            if provider.is_available():
                return provider
            logger.info("Gemini not configured; falling back to local heuristic.")

        elif name == "openai":
            provider = OpenAIProvider()
            if provider.is_available():
                return provider
            logger.info("OpenAI not configured; falling back to local heuristic.")

        elif name == "ollama":
            provider = OllamaProvider()
            if provider.is_available():
                return provider
            logger.info("Ollama not reachable; falling back to local heuristic.")

        # Default fallback: 100% offline local heuristic
        return LocalHeuristicPlanner()
