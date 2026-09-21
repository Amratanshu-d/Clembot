import re
import threading
import time
from typing import List, Optional

from app.ai.factory import AIProviderFactory
from app.commands.fast_router import FastCommandRouter
from app.commands.router import ActionRouter
from app.config.settings import settings
from app.context.context_manager import WindowsContextManager
from app.core.event_bus import event_bus
from app.core.models import (
    ActionResult,
    AgentAction,
    AgentPlan,
    AssistantState,
    ConfirmationRequest,
    ScreenContext,
)
from app.ai.language_detector import language_detector
from app.logging.logger import logger
from app.memory.conversation import ConversationalMemory
from app.security.guard import security_guard
from app.speech.normalizer import speech_normalizer
from app.speech.wake_word import WakeWordDetector
from app.tts.voice_service import voice_service


class AssistantOrchestrator:
    """
    Master assistant controller coordinating speech, context, fast routing, AI planning,
    security confirmations, action dispatching, and conversational memory.
    """

    def __init__(self):
        self.state = AssistantState.LISTENING if settings.active_on_startup else AssistantState.IDLE
        self.wake_detector = WakeWordDetector()
        self.fast_router = FastCommandRouter()
        self.ai_provider = AIProviderFactory.get_provider()
        self.context_manager = WindowsContextManager()
        self.memory = ConversationalMemory()
        self.router = ActionRouter()

        self.pending_confirmation: Optional[ConfirmationRequest] = None
        self._lock = threading.RLock()

        # Command deduplication / debounce tracking
        self._last_command_text: str = ""
        self._last_command_time: float = 0.0
        self._dedup_window_sec: float = 1.5

        # Wire event bus
        event_bus.subscribe("speech_recognized", self.handle_user_input)
        event_bus.subscribe("settings_updated", lambda _: self.reload_ai_provider())

    def reload_ai_provider(self) -> None:
        """Dynamically reloads the active AI provider when configuration updates."""
        with self._lock:
            self.ai_provider = AIProviderFactory.get_provider()
            logger.info(f"Active AI Provider updated to: {self.ai_provider.__class__.__name__}")

    def has_active_llm(self) -> bool:
        """Returns True if a cloud or local LLM (Gemini/Ollama) is active and available."""
        from app.ai.local_heuristic import LocalHeuristicPlanner
        return not isinstance(self.ai_provider, LocalHeuristicPlanner) and self.ai_provider.is_available()

    def set_state(self, new_state: AssistantState) -> None:
        with self._lock:
            old_state = self.state
            self.state = new_state
            logger.info(f"State transition: {old_state} -> {new_state}")
            event_bus.emit("assistant_state_changed", new_state.value)

    def activate(self) -> str:
        """Explicitly activates the assistant."""
        with self._lock:
            self.set_state(AssistantState.LISTENING)
            msg = "Clembot is activated and listening."
            voice_service.speak(msg)
            return msg

    def deactivate(self) -> str:
        """Explicitly deactivates the assistant."""
        with self._lock:
            self.set_state(AssistantState.IDLE)
            self.pending_confirmation = None
            msg = "Clembot deactivated. Say 'Clembot activate yourself' when you need me."
            voice_service.speak(msg)
            return msg

    def handle_user_input(self, text: str) -> None:
        """Main entry point for incoming user speech or text input."""
        raw_text = text.strip()
        if not raw_text:
            return

        with self._lock:
            # Normalize spoken phonetic variations (clemburt, clem ber, clembur -> clembot)
            cleaned = self.wake_detector.normalize_spoken_name(raw_text)

            # Deduplication to prevent double execution within 1.5s
            norm_check = re.sub(r'[^\w\s]', '', cleaned.lower()).strip()
            now = time.time()
            if norm_check and norm_check == self._last_command_text and (now - self._last_command_time) < self._dedup_window_sec:
                logger.info(f"Ignored duplicate command within {self._dedup_window_sec}s: \"{cleaned}\"")
                return

            self._last_command_text = norm_check
            self._last_command_time = now

            logger.info(f"User Input: \"{cleaned}\" (Current State: {self.state.value})")
            event_bus.emit("transcript_updated", f"You: {cleaned}")

            # 1. Check Activation Phrase
            is_wake, command_remainder = self.wake_detector.check_activation(cleaned)
            if is_wake:
                self.set_state(AssistantState.LISTENING)
                if not command_remainder:
                    msg = "Clembot activated. How can I help you?"
                    self._reply_and_record(msg)
                    return
                cleaned = command_remainder

            # 2. Check Deactivation Phrase
            if self.wake_detector.check_deactivation(cleaned):
                self.deactivate()
                return

            # If currently deactivated/sleeping, ignore ambient chatter until activated
            if self.state == AssistantState.IDLE:
                logger.debug("Ignored input because Clembot is deactivated (IDLE).")
                return

            # 3. Check Awaiting Confirmation State
            if self.state == AssistantState.AWAITING_CONFIRMATION and self.pending_confirmation:
                self._handle_confirmation_response(cleaned)
                return

            # 4. Strip any leading wake words like "Hey Clembot" if still present
            cleaned = self.wake_detector.strip_wake_phrase(cleaned)
            if not cleaned:
                self._reply_and_record("Yes, I'm listening.")
                return

            # 5. Process Regular Command
            self.process_command(cleaned)

    def process_command(self, raw_command: str) -> None:
        """Processes a validated user command."""
        self.set_state(AssistantState.PROCESSING)
        self.memory.add_user_turn(raw_command)

        # Normalize spoken fillers and homophones (e.g. "please open post grey sql" -> "open postgresql")
        normalized_cmd = speech_normalizer.normalize_command(raw_command)

        # A. Resolve Contextual Memory (e.g. "there" -> last visited folder)
        resolved_command = self.memory.resolve_contextual_references(normalized_cmd)
        if resolved_command != raw_command:
            logger.info(f"Normalized/Resolved command: \"{resolved_command}\"")

        # B. Check for non-English / Hinglish phrasing
        is_hinglish = language_detector.is_hinglish(normalized_cmd)
        has_llm = self.has_active_llm()

        plan = None
        if not is_hinglish:
            # Fast Command Router (Deterministic, 0ms latency)
            plan = self.fast_router.plan_for_command(resolved_command, llm_active=has_llm)
        else:
            logger.info(f"Hinglish / non-English query detected: '{normalized_cmd}'. Routing directly to AI reasoning.")

        # C. AI Planning Layer (LLM reasoning or open-ended speech)
        if not plan:
            self.set_state(AssistantState.PROCESSING)
            context = self.context_manager.capture_context()
            context.recent_history = self.memory.get_recent_history(limit=6)
            plan = self.ai_provider.plan(resolved_command, context)

        # D. Execute Plan
        self._dispatch_plan(plan)

    def _dispatch_plan(self, plan: AgentPlan) -> None:
        """Validates safety and dispatches planned actions."""
        if not plan.actions:
            self._reply_and_record(plan.reply or "I understood, but had no actions to take.")
            self.set_state(AssistantState.LISTENING)
            return

        # Check safety policy on all actions
        for action in plan.actions:
            requires_confirmation, conf_request = security_guard.evaluate_action_risk(action)
            if requires_confirmation and conf_request:
                self.pending_confirmation = conf_request
                self.set_state(AssistantState.AWAITING_CONFIRMATION)
                event_bus.emit("confirmation_requested", conf_request.model_dump())
                self._reply_and_record(conf_request.prompt)
                return

        # Safe to execute immediately
        self._execute_actions(plan.actions, plan.reply)

    def _execute_actions(self, actions: List[AgentAction], default_reply: str) -> None:
        """Executes actions sequentially and returns consolidated feedback."""
        self.set_state(AssistantState.EXECUTING)
        replies = []
        base_dir = self.memory.last_folder

        for action in actions:
            result = self.router.execute(action, context_base=base_dir)
            event_bus.emit("action_executed", result.model_dump())
            if result.message:
                replies.append(result.message)

        final_reply = " ".join(replies) if replies else default_reply
        self._reply_and_record(final_reply)
        self.set_state(AssistantState.LISTENING)

    def _handle_confirmation_response(self, response_text: str) -> None:
        """Handles user spoken response to a pending confirmation."""
        norm = response_text.lower().strip()
        positive = ["confirm", "yes", "do it", "sure", "proceed", "okay", "ok", "apply", "delete", "run"]
        negative = ["cancel", "no", "stop", "never mind", "dont", "do not", "abort"]

        if any(w in norm for w in positive):
            req = self.pending_confirmation
            self.pending_confirmation = None
            event_bus.emit("confirmation_resolved", {"id": req.id, "approved": True})
            self._execute_actions(req.actions, "Confirmed. Action executed.")

        elif any(w in norm for w in negative):
            req = self.pending_confirmation
            self.pending_confirmation = None
            event_bus.emit("confirmation_resolved", {"id": req.id, "approved": False})
            self._reply_and_record("Cancelled. No changes were made.")
            self.set_state(AssistantState.LISTENING)

        else:
            self._reply_and_record("I need your confirmation. Please say confirm to proceed, or cancel to abort.")

    def _reply_and_record(self, reply: str) -> None:
        """Speaks the reply and logs it in conversational history and event bus."""
        logger.info(f"Clembot Reply: \"{reply}\"")
        self.memory.add_clembot_turn(reply)
        event_bus.emit("clembot_replied", reply)
        voice_service.speak(reply)


# Global orchestrator singleton
orchestrator = AssistantOrchestrator()
