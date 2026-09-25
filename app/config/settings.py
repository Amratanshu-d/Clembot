import os
from pathlib import Path
from typing import List, Optional
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Load .env file from project root
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(ROOT_DIR / ".env")


class ClembotSettings(BaseModel):
    # App Information
    app_name: str = "Clembot"
    version: str = "1.0.0"
    debug: bool = Field(default_factory=lambda: os.getenv("CLEMBOT_DEBUG", "false").lower() == "true")
    
    # Audio & Voice Interaction
    # Specific user instruction:
    # "the voice assistant will get activated when the user say 'Clembot activate yourself',
    # and the voice assistant will turn off on saying 'Clembot deactivate'."
    wake_phrases: List[str] = [
        "clembot activate yourself",
        "clembot activate",
        "hey clembot",
        "activate yourself",
        "clembot"
    ]
    sleep_phrases: List[str] = [
        "clembot deactivate",
        "clembot deactivate yourself",
        "deactivate yourself",
        "clembot sleep",
        "clembot stop listening",
        "deactivate"
    ]
    
    # Modes
    push_to_talk: bool = Field(default_factory=lambda: os.getenv("CLEMBOT_PUSH_TO_TALK", "false").lower() == "true")
    continuous_listening: bool = True
    active_on_startup: bool = True
    start_with_windows: bool = False
    allow_unknown_actions: bool = Field(default_factory=lambda: os.getenv("CLEMBOT_ALLOW_UNKNOWN_ACTIONS", "false").lower() == "true")
    
    # Microphone & Speech Recognition
    mic_device_index: Optional[int] = None
    speech_energy_threshold: int = 300
    speech_dynamic_energy_threshold: bool = True
    speech_pause_threshold: float = 1.1
    speech_timeout: float = 5.0
    speech_phrase_time_limit: float = 12.0

    # STT Provider — "google" (default, cloud) or "whisper" (offline, faster-whisper)
    stt_provider: str = Field(default_factory=lambda: os.getenv("CLEMBOT_STT_PROVIDER", "google"))
    # Whisper model size: "tiny.en" (fastest/smallest), "base.en", "small.en", "medium.en"
    whisper_model_size: str = Field(default_factory=lambda: os.getenv("WHISPER_MODEL_SIZE", "tiny.en"))
    # Device for Whisper inference: "cpu" or "cuda" (requires NVIDIA GPU + CUDA)
    whisper_device: str = Field(default_factory=lambda: os.getenv("WHISPER_DEVICE", "cpu"))
    # Compute type: "int8" (smallest/fastest on CPU), "float16" (GPU), "float32"
    whisper_compute_type: str = Field(default_factory=lambda: os.getenv("WHISPER_COMPUTE_TYPE", "int8"))
    
    # Text-to-Speech (TTS)
    tts_enabled: bool = True
    tts_voice_id: Optional[str] = None
    tts_rate: int = 185  # words per minute
    tts_volume: float = 1.0
    
    # AI Providers & Keys
    # Providers: "heuristic" (offline rules), "gemini", "openai", "ollama", "groq"
    default_ai_provider: str = Field(default_factory=lambda: os.getenv("CLEMBOT_AI_PROVIDER", "gemini" if (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")) else "heuristic"))
    gemini_api_key: Optional[str] = Field(default_factory=lambda: os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"))
    openai_api_key: Optional[str] = Field(default_factory=lambda: os.getenv("OPENAI_API_KEY"))
    groq_api_key: Optional[str] = Field(default_factory=lambda: os.getenv("GROQ_API_KEY"))
    ollama_host: str = Field(default_factory=lambda: os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434"))
    ollama_model: str = Field(default_factory=lambda: os.getenv("OLLAMA_MODEL", "qwen3:4b"))
    ai_model_name: str = Field(default_factory=lambda: os.getenv("GEMINI_MODEL", "gemini-2.5-flash"))
    
    # Default Browser & Search Engine
    default_browser: str = "chrome"  # "chrome", "edge", "firefox", "default"
    default_search_engine: str = "google"  # "google", "bing", "duckduckgo", "youtube", "github"
    
    # IPC & VS Code Extension
    ipc_host: str = "127.0.0.1"
    ipc_port: int = 25362
    ipc_secret_token: str = Field(default_factory=lambda: os.getenv("CLEMBOT_IPC_TOKEN", "clembot-local-secure-token"))
    
    # Safety & Permissions
    confirm_destructive_actions: bool = True
    send_to_recycle_bin: bool = True
    show_code_diff_confirmation: bool = True
    
    # Logging
    log_level: str = "INFO"
    enable_detailed_logs: bool = True
    log_file: Path = ROOT_DIR / "clembot.log"


# Global settings singleton
settings = ClembotSettings()
