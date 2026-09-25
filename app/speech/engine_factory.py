"""
app/speech/engine_factory.py

Factory for selecting the active Speech-to-Text engine.

Usage (main.py):
    from app.speech.engine_factory import create_speech_engine
    speech_engine = create_speech_engine()

Controlled by CLEMBOT_STT_PROVIDER in .env:
  "google"  → SpeechEngine  (Google Cloud STT — default)
  "whisper" → WhisperEngine (faster-whisper offline STT)
"""

from app.config.settings import settings
from app.logging.logger import logger
from app.speech.base import BaseSpeechRecognizer


def create_speech_engine() -> BaseSpeechRecognizer:
    """
    Returns the configured STT engine.

    Falls back to Google STT automatically if:
      - stt_provider is "whisper" but faster-whisper is not installed
      - WhisperModel fails to initialise
    """
    provider = settings.stt_provider.strip().lower()

    if provider == "whisper":
        try:
            # Verify faster-whisper is importable before committing
            import faster_whisper  # noqa: F401
            from app.speech.whisper_engine import WhisperEngine
            logger.info(
                f"STT provider: Whisper (model={settings.whisper_model_size}, "
                f"device={settings.whisper_device}, compute={settings.whisper_compute_type})"
            )
            return WhisperEngine()
        except ImportError:
            logger.warning(
                "CLEMBOT_STT_PROVIDER=whisper was requested but faster-whisper is not installed. "
                "Falling back to Google STT. Run: pip install faster-whisper"
            )
        except Exception as e:
            logger.warning(f"WhisperEngine failed to initialise ({e}). Falling back to Google STT.")

    # Default: Google Speech Recognition via SpeechRecognition library
    from app.speech.engine import SpeechEngine
    logger.info("STT provider: Google Speech Recognition (cloud)")
    return SpeechEngine()
