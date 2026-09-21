import math
import threading
import time
from typing import Optional
import customtkinter as ctk

from app.config.settings import settings
from app.core.event_bus import event_bus
from app.core.models import AssistantState
from app.core.orchestrator import orchestrator
from app.logging.logger import logger
from app.speech.engine import SpeechEngine
from app.ui.settings_dialog import SettingsDialog
from app.ui.theme import COLORS, FONTS


class ClembotMainWindow(ctk.CTk):
    """
    Primary modern Windows desktop GUI for Clembot Voice Assistant.
    """

    def __init__(self, speech_engine: Optional[SpeechEngine] = None):
        super().__init__()

        # Window settings
        self.title("Clembot — Windows Voice Assistant")
        self.geometry("960x720")
        self.minsize(800, 600)
        self.configure(fg_color=COLORS["bg_dark"])

        self.speech_engine = speech_engine
        self._pulse_angle = 0
        self._is_animating = True
        self._current_confirmation_id: Optional[str] = None

        self._build_header()
        self._build_visualizer()
        self._build_confirmation_banner()
        self._build_main_panels()
        self._build_input_bar()

        # Connect to EventBus
        self._register_event_handlers()

        # Start visual pulse animation thread
        self.after(50, self._animate_pulse)

    def _build_header(self):
        """Top title bar with status badge and toggles."""
        self.header_frame = ctk.CTkFrame(self, height=65, fg_color=COLORS["sidebar_bg"], corner_radius=0)
        self.header_frame.pack(fill="x", side="top")

        # App branding
        brand_frame = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        brand_frame.pack(side="left", padx=20, pady=12)

        logo_label = ctk.CTkLabel(brand_frame, text="⚡", font=("Segoe UI", 20))
        logo_label.pack(side="left", padx=(0, 8))

        title_label = ctk.CTkLabel(brand_frame, text="Clembot", font=FONTS["title"], text_color=COLORS["text_primary"])
        title_label.pack(side="left")

        version_label = ctk.CTkLabel(brand_frame, text=f"v{settings.version}", font=FONTS["small"], text_color=COLORS["text_muted"])
        version_label.pack(side="left", padx=(8, 0), pady=(4, 0))

        # Right side controls: State Badge, Activation Toggle, Settings
        controls_frame = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        controls_frame.pack(side="right", padx=20, pady=12)

        self.status_badge = ctk.CTkLabel(
            controls_frame,
            text="LISTENING",
            font=FONTS["subtitle"],
            text_color=COLORS["listening_pulse"],
            fg_color=COLORS["card_bg"],
            corner_radius=12,
            padx=14,
            pady=4
        )
        self.status_badge.pack(side="left", padx=10)

        self.activation_switch = ctk.CTkSwitch(
            controls_frame,
            text="Active",
            font=FONTS["body_bold"],
            command=self._on_toggle_activation
        )
        if orchestrator.state != AssistantState.IDLE:
            self.activation_switch.select()
        self.activation_switch.pack(side="left", padx=10)

        settings_btn = ctk.CTkButton(
            controls_frame,
            text="⚙ Settings",
            font=FONTS["body"],
            width=90,
            height=32,
            fg_color=COLORS["card_bg"],
            hover_color=COLORS["card_border"],
            command=self._open_settings
        )
        settings_btn.pack(side="left", padx=5)

    def _build_visualizer(self):
        """Audio waveform / glowing pulse visualizer."""
        self.viz_frame = ctk.CTkFrame(self, height=50, fg_color="transparent")
        self.viz_frame.pack(fill="x", padx=25, pady=(8, 4))

        self.canvas = ctk.CTkCanvas(self.viz_frame, height=40, bg=COLORS["bg_dark"], highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

    def _build_confirmation_banner(self):
        """Interactive confirmation banner for destructive actions and Code Diffs."""
        self.conf_frame = ctk.CTkFrame(
            self,
            fg_color=COLORS["card_bg"],
            border_color=COLORS["warning"],
            border_width=2,
            corner_radius=10
        )
        # Initially hidden until confirmation_requested
        self.conf_prompt = ctk.CTkLabel(
            self.conf_frame,
            text="Action requires confirmation",
            font=FONTS["subtitle"],
            text_color=COLORS["warning"],
            wraplength=800
        )
        self.conf_prompt.pack(anchor="w", padx=20, pady=(12, 6))

        # Diff box (for code modifications)
        self.diff_text = ctk.CTkTextbox(
            self.conf_frame,
            height=120,
            font=FONTS["code"],
            fg_color=COLORS["input_bg"],
            text_color="#98c379"
        )

        btn_row = ctk.CTkFrame(self.conf_frame, fg_color="transparent")
        btn_row.pack(anchor="e", padx=20, pady=(6, 12))

        self.btn_confirm = ctk.CTkButton(
            btn_row,
            text="✔ Confirm (Yes)",
            font=FONTS["body_bold"],
            fg_color=COLORS["success"],
            width=130,
            command=self._on_user_confirm
        )
        self.btn_confirm.pack(side="left", padx=6)

        self.btn_cancel = ctk.CTkButton(
            btn_row,
            text="✖ Cancel (No)",
            font=FONTS["body_bold"],
            fg_color=COLORS["danger"],
            width=110,
            command=self._on_user_cancel
        )
        self.btn_cancel.pack(side="left", padx=6)

    def _build_main_panels(self):
        """Two-column layout: Left is conversation dialogue; Right is activity log."""
        panels = ctk.CTkFrame(self, fg_color="transparent")
        panels.pack(fill="both", expand=True, padx=20, pady=5)

        # Left Column: Conversation Dialogue
        left_col = ctk.CTkFrame(panels, fg_color=COLORS["card_bg"], corner_radius=10)
        left_col.pack(side="left", fill="both", expand=True, padx=(0, 10))

        ctk.CTkLabel(left_col, text="Conversation Transcript", font=FONTS["subtitle"], text_color=COLORS["text_secondary"]).pack(anchor="w", padx=15, pady=(12, 4))

        self.dialogue_box = ctk.CTkTextbox(
            left_col,
            font=FONTS["body"],
            fg_color=COLORS["bg_dark"],
            text_color=COLORS["text_primary"],
            wrap="word",
            corner_radius=8
        )
        self.dialogue_box.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        self.dialogue_box.insert("end", "Clembot initialized. Say 'Clembot activate yourself' to begin.\n\n")

        # Right Column: Activity History
        right_col = ctk.CTkFrame(panels, width=320, fg_color=COLORS["card_bg"], corner_radius=10)
        right_col.pack(side="right", fill="both", padx=(5, 0))

        ctk.CTkLabel(right_col, text="Action Log", font=FONTS["subtitle"], text_color=COLORS["text_secondary"]).pack(anchor="w", padx=15, pady=(12, 4))

        self.activity_box = ctk.CTkTextbox(
            right_col,
            width=300,
            font=FONTS["small"],
            fg_color=COLORS["bg_dark"],
            text_color=COLORS["text_secondary"],
            wrap="word",
            corner_radius=8
        )
        self.activity_box.pack(fill="both", expand=True, padx=12, pady=(0, 12))

    def _build_input_bar(self):
        """Bottom bar with Push-to-Talk and text entry."""
        bar = ctk.CTkFrame(self, height=55, fg_color=COLORS["sidebar_bg"], corner_radius=0)
        bar.pack(fill="x", side="bottom")

        # Push-to-talk button
        self.ptt_btn = ctk.CTkButton(
            bar,
            text="🎙 Push to Talk",
            font=FONTS["body_bold"],
            width=140,
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            command=self._on_ptt_clicked
        )
        self.ptt_btn.pack(side="left", padx=15, pady=10)

        # Text input entry
        self.input_entry = ctk.CTkEntry(
            bar,
            placeholder_text="Or type a voice command here (e.g. 'Open Downloads', 'Search Google for Django')...",
            font=FONTS["body"],
            fg_color=COLORS["input_bg"]
        )
        self.input_entry.pack(side="left", fill="x", expand=True, padx=(5, 10), pady=10)
        self.input_entry.bind("<Return>", lambda e: self._on_send_typed())

        # Send button
        send_btn = ctk.CTkButton(
            bar,
            text="Send",
            font=FONTS["body_bold"],
            width=80,
            fg_color=COLORS["card_bg"],
            hover_color=COLORS["card_border"],
            command=self._on_send_typed
        )
        send_btn.pack(side="right", padx=(0, 15), pady=10)

    def _register_event_handlers(self):
        event_bus.subscribe("assistant_state_changed", self._on_state_changed)
        event_bus.subscribe("transcript_updated", self._append_dialogue)
        event_bus.subscribe("clembot_replied", self._append_dialogue)
        event_bus.subscribe("action_executed", self._on_action_logged)
        event_bus.subscribe("confirmation_requested", self._show_confirmation_modal)
        event_bus.subscribe("confirmation_resolved", lambda _: self._hide_confirmation_modal())

    def _on_state_changed(self, state_val: str):
        self.after(0, lambda: self._update_badge(state_val))

    def _update_badge(self, state_val: str):
        self.status_badge.configure(text=state_val)
        if state_val == "LISTENING":
            self.status_badge.configure(text_color=COLORS["listening_pulse"])
        elif state_val == "PROCESSING" or state_val == "EXECUTING":
            self.status_badge.configure(text_color=COLORS["accent_glow"])
        elif state_val == "AWAITING_CONFIRMATION":
            self.status_badge.configure(text_color=COLORS["warning"])
        else:
            self.status_badge.configure(text_color=COLORS["text_muted"])

    def _append_dialogue(self, message: str):
        self.after(0, lambda: self._safe_append_dialogue(message))

    def _safe_append_dialogue(self, message: str):
        self.dialogue_box.insert("end", f"{message}\n\n")
        self.dialogue_box.see("end")

    def _on_action_logged(self, action_dict: dict):
        self.after(0, lambda: self._safe_append_activity(action_dict))

    def _safe_append_activity(self, action_dict: dict):
        act_type = action_dict.get("action_type", "")
        success = action_dict.get("success", True)
        msg = action_dict.get("message", "")
        symbol = "✔" if success else "✖"
        log_entry = f"[{symbol}] {act_type.upper()}: {msg}\n"
        self.activity_box.insert("end", log_entry)
        self.activity_box.see("end")

    def _show_confirmation_modal(self, conf_dict: dict):
        self.after(0, lambda: self._safe_show_confirmation(conf_dict))

    def _safe_show_confirmation(self, conf_dict: dict):
        prompt = conf_dict.get("prompt", "Please confirm this action.")
        self.conf_prompt.configure(text=prompt)
        diff = conf_dict.get("diff_text")
        if diff:
            self.diff_text.pack(fill="x", padx=20, pady=(0, 10))
            self.diff_text.delete("1.0", "end")
            self.diff_text.insert("end", diff)
        else:
            self.diff_text.pack_forget()

        self.conf_frame.pack(fill="x", padx=20, pady=8, before=self.viz_frame)

    def _hide_confirmation_modal(self):
        self.after(0, lambda: self.conf_frame.pack_forget())

    def _on_user_confirm(self):
        self._hide_confirmation_modal()
        threading.Thread(target=lambda: orchestrator.handle_user_input("confirm"), daemon=True).start()

    def _on_user_cancel(self):
        self._hide_confirmation_modal()
        threading.Thread(target=lambda: orchestrator.handle_user_input("cancel"), daemon=True).start()

    def _on_toggle_activation(self):
        if self.activation_switch.get():
            orchestrator.activate()
        else:
            orchestrator.deactivate()

    def _on_ptt_clicked(self):
        if self.speech_engine:
            threading.Thread(target=self._run_ptt, daemon=True).start()

    def _run_ptt(self):
        self.ptt_btn.configure(text="🔴 Listening...", fg_color=COLORS["danger"])
        self.speech_engine.listen_once(timeout=6.0)
        self.ptt_btn.configure(text="🎙 Push to Talk", fg_color=COLORS["accent"])

    def _on_send_typed(self):
        text = self.input_entry.get().strip()
        if text:
            self.input_entry.delete(0, "end")
            threading.Thread(target=lambda: orchestrator.handle_user_input(text), daemon=True).start()

    def _open_settings(self):
        SettingsDialog(self)

    def _animate_pulse(self):
        """Renders audio waveform pulse when active or processing."""
        if self._is_animating:
            self.canvas.delete("all")
            width = self.canvas.winfo_width() or 900
            height = self.canvas.winfo_height() or 40
            mid_y = height // 2

            is_active = orchestrator.state in [AssistantState.LISTENING, AssistantState.PROCESSING, AssistantState.SPEAKING]
            color = COLORS["listening_pulse"] if is_active else COLORS["text_muted"]

            points = []
            num_points = 35
            for i in range(num_points):
                x = (width / (num_points - 1)) * i
                if is_active:
                    amplitude = 12 * math.sin(self._pulse_angle + i * 0.4)
                else:
                    amplitude = 1.5 * math.sin(self._pulse_angle + i * 0.2)
                points.append((x, mid_y + amplitude))

            for i in range(len(points) - 1):
                self.canvas.create_line(
                    points[i][0], points[i][1],
                    points[i + 1][0], points[i + 1][1],
                    fill=color, width=2.5
                )

            self._pulse_angle += 0.15

        self.after(50, self._animate_pulse)
