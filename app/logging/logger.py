import logging
import re
from typing import Any
from app.config.settings import settings


class SensitiveDataFilter(logging.Filter):
    """Redacts API keys, passwords, tokens, and authorization headers from logs."""

    PATTERNS = [
        (re.compile(r'(api[-_]?key|token|secret|password|bearer\s+)["\':=\s]+([A-Za-z0-9_\-\.]{8,})', re.IGNORECASE), r'\1=***REDACTED***'),
        (re.compile(r'(AIzaSy[A-Za-z0-9_-]{33})'), '***GEMINI_API_KEY_REDACTED***'),
        (re.compile(r'(sk-[A-Za-z0-9_-]{32,})'), '***OPENAI_KEY_REDACTED***'),
        (re.compile(r'(gsk_[A-Za-z0-9_-]{32,})'), '***GROQ_KEY_REDACTED***'),
    ]

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            for pattern, replacement in self.PATTERNS:
                record.msg = pattern.sub(replacement, record.msg)
        return True


def setup_logger(name: str = "clembot") -> logging.Logger:
    """Configures structured, privacy-safe logger for Clembot."""
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))
    logger.propagate = False

    if not logger.handlers:
        # Console Handler with formatting
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter(
            "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
            datefmt="%H:%M:%S"
        )
        console_handler.setFormatter(console_formatter)
        console_handler.addFilter(SensitiveDataFilter())
        logger.addHandler(console_handler)

        # Optional File Handler
        if settings.enable_detailed_logs:
            try:
                settings.log_file.parent.mkdir(parents=True, exist_ok=True)
                file_handler = logging.FileHandler(settings.log_file, encoding="utf-8")
                file_handler.setLevel(logging.DEBUG)
                file_formatter = logging.Formatter(
                    "%(asctime)s | %(levelname)-7s | %(name)s | %(filename)s:%(lineno)d | %(message)s"
                )
                file_handler.setFormatter(file_formatter)
                file_handler.addFilter(SensitiveDataFilter())
                logger.addHandler(file_handler)
            except Exception as e:
                print(f"Failed to initialize file logger: {e}")

    return logger


logger = setup_logger()
