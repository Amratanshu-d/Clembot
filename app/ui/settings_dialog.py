import os
import tkinter as tk
from typing import Callable, Optional
import customtkinter as ctk

from app.config.settings import settings
from app.logging.logger import logger
from app.speech.engine import SpeechEngine
from app.tts.sapi_engine import SAPIEngine
from app.ui.theme import COLORS, FONTS


class SettingsDialog(ctk.CTkToplevel):
    """
    Settings window for Clembot configuration (Microphone, Voice, AI Providers, Browser, Safety).
    """

    def __init__(self, parent, on_save_callback: Optional[Callable[[], None]] = None):
        super().__init__(parent)
        self.title("Clembot Settings")
        self.geometry("640x620")
        self.resizable(False, False)
        self.configure(fg_color=COLORS["bg_dark"])
        self.on_save_callback = on_save_callback

        self.transient(parent)
        self.grab_set()

        self._build_ui()

    def _build_ui(self):
        # Header
        header = ctk.CTkLabel(
            self,
            text="Preferences & Configuration",
            font=FONTS["title"],
            text_color=COLORS["text_primary"]
        )
        header.pack(anchor="w", padx=25, pady=(20, 10))

        # Tabview
        tabs = ctk.CTkTabview(self, fg_color=COLORS["card_bg"], segmented_button_selected_color=COLORS["accent"])
        tabs.pack(fill="both", expand=True, padx=20, pady=10)

        tab_audio = tabs.add("Audio & Speech")
        tab_ai = tabs.add("AI & Models")
        tab_general = tabs.add("System & Safety")

        # --- 1. Audio & Speech Tab ---
        ctk.CTkLabel(tab_audio, text="Microphone Device:", font=FONTS["body_bold"]).pack(anchor="w", padx=15, pady=(10, 2))
        mics = SpeechEngine.get_microphones()
        self.mic_var = ctk.StringVar(value=mics[settings.mic_device_index] if settings.mic_device_index is not None and settings.mic_device_index < len(mics) else mics[0])
        mic_combo = ctk.CTkComboBox(tab_audio, values=mics, variable=self.mic_var, width=450)
        mic_combo.pack(anchor="w", padx=15, pady=(0, 15))

        ctk.CTkLabel(tab_audio, text="TTS Voice:", font=FONTS["body_bold"]).pack(anchor="w", padx=15, pady=(5, 2))
        voices = SAPIEngine().get_voices()
        voice_names = [v["name"] for v in voices] or ["Default System Voice"]
        self.voice_var = ctk.StringVar(value=voice_names[0])
        voice_combo = ctk.CTkComboBox(tab_audio, values=voice_names, variable=self.voice_var, width=450)
        voice_combo.pack(anchor="w", padx=15, pady=(0, 15))

        ctk.CTkLabel(tab_audio, text=f"Speech Rate (WPM): {settings.tts_rate}", font=FONTS["body"]).pack(anchor="w", padx=15, pady=(5, 2))
        self.rate_slider = ctk.CTkSlider(tab_audio, from_=100, to=300, number_of_steps=20)
        self.rate_slider.set(settings.tts_rate)
        self.rate_slider.pack(fill="x", padx=15, pady=(0, 15))

        self.ptt_switch = ctk.CTkSwitch(tab_audio, text="Push-to-Talk Mode (disable continuous listening)")
        if settings.push_to_talk:
            self.ptt_switch.select()
        self.ptt_switch.pack(anchor="w", padx=15, pady=10)

        # --- 2. AI & Models Tab ---
        ctk.CTkLabel(tab_ai, text="AI Intent Provider:", font=FONTS["body_bold"]).pack(anchor="w", padx=15, pady=(10, 2))
        providers = ["heuristic", "gemini", "openai", "ollama"]
        self.provider_var = ctk.StringVar(value=settings.default_ai_provider)
        provider_combo = ctk.CTkComboBox(tab_ai, values=providers, variable=self.provider_var, width=300)
        provider_combo.pack(anchor="w", padx=15, pady=(0, 15))

        ctk.CTkLabel(tab_ai, text="Google Gemini API Key:", font=FONTS["body"]).pack(anchor="w", padx=15, pady=(5, 2))
        self.gemini_key_entry = ctk.CTkEntry(tab_ai, width=450, show="*", placeholder_text="AIzaSy...")
        if settings.gemini_api_key:
            self.gemini_key_entry.insert(0, settings.gemini_api_key)
        self.gemini_key_entry.pack(anchor="w", padx=15, pady=(0, 15))

        ctk.CTkLabel(tab_ai, text="OpenAI API Key:", font=FONTS["body"]).pack(anchor="w", padx=15, pady=(5, 2))
        self.openai_key_entry = ctk.CTkEntry(tab_ai, width=450, show="*", placeholder_text="sk-...")
        if settings.openai_api_key:
            self.openai_key_entry.insert(0, settings.openai_api_key)
        self.openai_key_entry.pack(anchor="w", padx=15, pady=(0, 15))

        ctk.CTkLabel(tab_ai, text="Ollama Local Host:", font=FONTS["body"]).pack(anchor="w", padx=15, pady=(5, 2))
        self.ollama_entry = ctk.CTkEntry(tab_ai, width=450)
        self.ollama_entry.insert(0, settings.ollama_host)
        self.ollama_entry.pack(anchor="w", padx=15, pady=(0, 15))

        # --- 3. System & Safety Tab ---
        ctk.CTkLabel(tab_general, text="Default Web Browser:", font=FONTS["body_bold"]).pack(anchor="w", padx=15, pady=(10, 2))
        browsers = ["chrome", "edge", "firefox"]
        self.browser_var = ctk.StringVar(value=settings.default_browser)
        browser_combo = ctk.CTkComboBox(tab_general, values=browsers, variable=self.browser_var, width=250)
        browser_combo.pack(anchor="w", padx=15, pady=(0, 15))

        self.recycle_bin_switch = ctk.CTkSwitch(tab_general, text="Always send deleted files to Windows Recycle Bin")
        if settings.send_to_recycle_bin:
            self.recycle_bin_switch.select()
        self.recycle_bin_switch.pack(anchor="w", padx=15, pady=10)

        self.diff_switch = ctk.CTkSwitch(tab_general, text="Require interactive Code Diff confirmation for file modifications")
        if settings.show_code_diff_confirmation:
            self.diff_switch.select()
        self.diff_switch.pack(anchor="w", padx=15, pady=10)

        # Buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=(10, 15), side="bottom")

        save_btn = ctk.CTkButton(
            btn_frame,
            text="Save Preferences",
            font=FONTS["body_bold"],
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            command=self._save
        )
        save_btn.pack(side="right", padx=5)

        cancel_btn = ctk.CTkButton(
            btn_frame,
            text="Cancel",
            font=FONTS["body"],
            fg_color=COLORS["card_bg"],
            command=self.destroy
        )
        cancel_btn.pack(side="right", padx=5)

    def _save(self):
        settings.default_ai_provider = self.provider_var.get()
        settings.gemini_api_key = self.gemini_key_entry.get().strip() or None
        settings.openai_api_key = self.openai_key_entry.get().strip() or None
        settings.ollama_host = self.ollama_entry.get().strip()
        settings.default_browser = self.browser_var.get()
        settings.tts_rate = int(self.rate_slider.get())
        settings.push_to_talk = bool(self.ptt_switch.get())
        settings.send_to_recycle_bin = bool(self.recycle_bin_switch.get())
        settings.show_code_diff_confirmation = bool(self.diff_switch.get())

        logger.info("Settings updated successfully.")

        # Persist updated configuration to .env file
        try:
            from app.config.settings import ROOT_DIR
            env_path = ROOT_DIR / ".env"
            env_content = f"""# Clembot Environment Configuration
CLEMBOT_AI_PROVIDER={settings.default_ai_provider}
GEMINI_API_KEY={settings.gemini_api_key or ''}
OPENAI_API_KEY={settings.openai_api_key or ''}
OLLAMA_HOST={settings.ollama_host}
OLLAMA_MODEL={settings.ollama_model}
CLEMBOT_DEFAULT_BROWSER={settings.default_browser}
CLEMBOT_PUSH_TO_TALK={str(settings.push_to_talk).lower()}
"""
            with open(env_path, "w", encoding="utf-8") as f:
                f.write(env_content)
            logger.info("Settings persisted to .env")
        except Exception as e:
            logger.warning(f"Could not write .env: {e}")

        from app.core.event_bus import event_bus
        event_bus.emit("settings_updated")

        if self.on_save_callback:
            self.on_save_callback()
        self.destroy()
