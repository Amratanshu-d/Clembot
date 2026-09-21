import os
import socket
import sys
from pathlib import Path
from typing import Dict, List, Tuple


class SystemDoctor:
    """
    Pre-flight diagnostic doctor that checks system health, required packages,
    audio input/output, IPC ports, and AI provider configurations.
    """

    CRITICAL_PACKAGES = [
        ("win32gui", "pywin32"),
        ("customtkinter", "customtkinter"),
        ("sounddevice", "sounddevice"),
        ("speech_recognition", "SpeechRecognition"),
        ("pyttsx3", "pyttsx3"),
        ("rapidfuzz", "rapidfuzz"),
        ("jellyfish", "jellyfish"),
        ("psutil", "psutil"),
        ("pydantic", "pydantic"),
        ("fastapi", "fastapi"),
        ("uvicorn", "uvicorn"),
        ("send2trash", "send2trash"),
    ]

    @classmethod
    def check_python_version(cls) -> Tuple[bool, str]:
        major, minor, micro = sys.version_info[:3]
        ver_str = f"{major}.{minor}.{micro}"
        if major == 3 and minor >= 10:
            return True, f"Python {ver_str} (>= 3.10 requirement satisfied)"
        return False, f"Python {ver_str} is unsupported. Python 3.10+ is required."

    @classmethod
    def check_packages(cls) -> List[Tuple[str, bool, str]]:
        results = []
        for mod_name, pkg_name in cls.CRITICAL_PACKAGES:
            try:
                __import__(mod_name)
                results.append((pkg_name, True, "Installed and importable"))
            except ImportError as e:
                results.append((pkg_name, False, f"Missing or broken ({e})"))
        return results

    @classmethod
    def check_audio_input(cls) -> Tuple[bool, str]:
        try:
            import sounddevice as sd
            devices = sd.query_devices()
            input_mics = [d["name"] for d in devices if d.get("max_input_channels", 0) > 0]
            if input_mics:
                return True, f"Found {len(input_mics)} input microphone(s): {input_mics[0]}"
            return False, "No active audio input microphones found on this system."
        except Exception as e:
            return False, f"SoundDevice error querying audio input: {e}"

    @classmethod
    def check_tts_engine(cls) -> Tuple[bool, str]:
        try:
            import pyttsx3
            engine = pyttsx3.init()
            voices = engine.getProperty("voices")
            v_count = len(voices) if voices else 0
            return True, f"Windows SAPI voice engine initialized ({v_count} voices available)"
        except Exception as e:
            return False, f"TTS engine failed to initialize: {e}"

    @classmethod
    def check_ipc_port(cls, port: int = 25362) -> Tuple[bool, str]:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.bind(("127.0.0.1", port))
            s.close()
            return True, f"Port {port} is available for local VS Code bridge IPC"
        except OSError:
            return True, f"Port {port} is already in use (possibly by a running Clembot instance)"
        finally:
            s.close()

    @classmethod
    def check_ai_provider(cls) -> Tuple[bool, str]:
        from app.config.settings import settings
        provider = settings.default_ai_provider.lower()

        if provider == "gemini":
            if settings.gemini_api_key and settings.gemini_api_key.strip():
                return True, "Google Gemini configured with active API key"
            return False, "Gemini selected but GEMINI_API_KEY is missing in .env"
        elif provider == "ollama":
            try:
                import httpx
                r = httpx.get(f"{settings.ollama_host}/api/version", timeout=1.5)
                if r.status_code == 200:
                    return True, f"Local Ollama reachable at {settings.ollama_host}"
                return False, f"Ollama returned HTTP {r.status_code}"
            except Exception:
                return False, f"Cannot connect to Ollama at {settings.ollama_host}"
        elif provider == "openai":
            if settings.openai_api_key:
                return True, "OpenAI configured with active API key"
            return False, "OpenAI selected but OPENAI_API_KEY is missing in .env"
        else:
            return True, "Offline Local Heuristic provider active (100% offline rules)"

    @classmethod
    def check_app_catalog(cls) -> Tuple[bool, str]:
        cache_dir = Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local"))) / "Clembot"
        cache_file = cache_dir / "app_index.json"
        if cache_file.exists():
            return True, f"App catalog cache present at {cache_file}"
        return True, "App catalog cache will be generated on first startup"

    @classmethod
    def run_all(cls) -> bool:
        print("=" * 65)
        print("  CLEMBOT SYSTEM HEALTH DOCTOR -- Windows 10/11 Diagnostic")
        print("=" * 65)

        all_ok = True

        # 1. Python Version
        ok, msg = cls.check_python_version()
        symbol = "[PASS]" if ok else "[FAIL]"
        print(f"{symbol:7} Python Version : {msg}")
        if not ok:
            all_ok = False

        # 2. Critical Packages
        print("\n--- Required Dependencies ---")
        pkg_results = cls.check_packages()
        for pkg, ok, msg in pkg_results:
            symbol = "[PASS]" if ok else "[FAIL]"
            print(f"{symbol:7} {pkg:20} : {msg}")
            if not ok:
                all_ok = False

        # 3. Audio & Speech
        print("\n--- Audio & Speech Subsystems ---")
        ok, msg = cls.check_audio_input()
        symbol = "[PASS]" if ok else "[WARN]"
        print(f"{symbol:7} Audio Input Mics : {msg}")

        ok, msg = cls.check_tts_engine()
        symbol = "[PASS]" if ok else "[FAIL]"
        print(f"{symbol:7} Text-to-Speech   : {msg}")
        if not ok:
            all_ok = False

        # 4. IPC Bridge
        print("\n--- Local IPC Network ---")
        ok, msg = cls.check_ipc_port()
        symbol = "[PASS]" if ok else "[WARN]"
        print(f"{symbol:7} Local IPC Port   : {msg}")

        # 5. AI Provider
        print("\n--- AI Intelligence Provider ---")
        ok, msg = cls.check_ai_provider()
        symbol = "[PASS]" if ok else "[WARN]"
        print(f"{symbol:7} AI Provider      : {msg}")

        # 6. App Catalog
        print("\n--- Application Catalog ---")
        ok, msg = cls.check_app_catalog()
        symbol = "[PASS]" if ok else "[INFO]"
        print(f"{symbol:7} App Index Cache  : {msg}")

        print("=" * 65)
        if all_ok:
            print("  STATUS: ALL CRITICAL SUBSYSTEMS OPERATIONAL (100% HEALTHY)")
        else:
            print("  STATUS: ISSUES DETECTED. PLEASE REVIEW THE FAILED ITEMS ABOVE.")
        print("=" * 65)

        return all_ok


if __name__ == "__main__":
    success = SystemDoctor.run_all()
    sys.exit(0 if success else 1)
