from abc import ABC, abstractmethod
from typing import Callable, Optional


class BaseSpeechRecognizer(ABC):
    """Abstract interface for speech-to-text recognition providers."""

    @abstractmethod
    def start(self, on_speech_recognized: Callable[[str], None], on_error: Optional[Callable[[str], None]] = None) -> None:
        """Start listening for speech."""
        pass

    @abstractmethod
    def stop(self) -> None:
        """Stop listening."""
        pass

    @abstractmethod
    def listen_once(self, timeout: float = 5.0) -> Optional[str]:
        """Synchronously capture a single utterance."""
        pass
