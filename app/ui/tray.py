import threading
from typing import Callable, Optional
from PIL import Image, ImageDraw
import pystray

from app.core.models import AssistantState
from app.core.orchestrator import orchestrator
from app.logging.logger import logger


def create_tray_icon_image() -> Image.Image:
    """Generates a modern 64x64 RGBA icon for the Windows system tray."""
    image = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    # Outer circle with Fluent blue accent
    draw.ellipse((4, 4, 60, 60), fill="#0078D4", outline="#4CC2FF", width=2)
    # Inner stylized lightning bolt / "C" mark
    draw.polygon([(34, 12), (20, 34), (32, 34), (28, 52), (46, 28), (34, 28)], fill="#FFFFFF")
    return image


class ClembotSystemTray:
    """
    Windows System Tray icon manager for background operation.
    """

    def __init__(
        self,
        on_show_window: Optional[Callable[[], None]] = None,
        on_exit: Optional[Callable[[], None]] = None
    ):
        self.on_show_window = on_show_window
        self.on_exit = on_exit
        self.icon: Optional[pystray.Icon] = None
        self._thread: Optional[threading.Thread] = None

    def _toggle_listening(self, icon, item):
        if orchestrator.state == AssistantState.IDLE:
            orchestrator.activate()
        else:
            orchestrator.deactivate()

    def _show_window_action(self, icon, item):
        if self.on_show_window:
            self.on_show_window()

    def _exit_action(self, icon, item):
        logger.info("Exiting Clembot via System Tray.")
        if self.icon:
            self.icon.stop()
        if self.on_exit:
            self.on_exit()

    def start(self):
        """Launches the system tray icon in a dedicated background thread."""
        image = create_tray_icon_image()

        menu = pystray.Menu(
            pystray.MenuItem("Open Dashboard", self._show_window_action, default=True),
            pystray.MenuItem(
                "Listening Active",
                self._toggle_listening,
                checked=lambda item: orchestrator.state != AssistantState.IDLE
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Exit Clembot", self._exit_action)
        )

        self.icon = pystray.Icon("Clembot", image, "Clembot Voice Assistant", menu)

        def _run():
            try:
                self.icon.run()
            except Exception as e:
                logger.error(f"System tray error: {e}")

        self._thread = threading.Thread(target=_run, daemon=True, name="Clembot-SystemTray")
        self._thread.start()
        logger.info("Windows System Tray icon initialized.")

    def stop(self):
        if self.icon:
            self.icon.stop()
