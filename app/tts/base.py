from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class BaseTTSProvider(ABC):
    """Abstract interface for text-to-speech engines."""

    @abstractmethod
    def speak(self, text: str) -> None:
        """Speak the given text."""
        pass

    @abstractmethod
    def stop(self) -> None:
        """Stop current speech output immediately."""
        pass

    @abstractmethod
    def get_voices(self) -> List[Dict[str, Any]]:
        """List available voices."""
        pass

    @abstractmethod
    def set_voice(self, voice_id: str) -> None:
        """Select a voice by ID."""
        pass

    @abstractmethod
    def set_rate(self, rate: int) -> None:
        """Set speech rate (words per minute)."""
        pass

    @abstractmethod
    def set_volume(self, volume: float) -> None:
        """Set volume (0.0 to 1.0)."""
        pass
