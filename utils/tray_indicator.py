import os
import threading
from PIL import Image, ImageDraw
import pystray
from utils.logger import logger

class TrayIndicator:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(TrayIndicator, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self.icon = None
        self.state_colors = {
            "sleeping": "gray",
            "listening": "green",
            "processing": "blue",
            "speaking": "purple",
            "error": "red"
        }
        self.current_state = "sleeping"
        self.thread = None
        self._initialized = True

    def start(self):
        """Starts the tray icon in a background thread."""
        self.thread = threading.Thread(target=self._run_icon, daemon=True)
        self.thread.start()

    def _run_icon(self):
        try:
            image = self._create_circle_image(self.state_colors[self.current_state])
            menu = pystray.Menu(
                pystray.MenuItem('Exit Assistant', self._on_exit)
            )
            self.icon = pystray.Icon("AI_Assistant", image, "AI Desktop Assistant", menu)
            self.icon.run()
        except Exception as e:
            logger.log_error(f"Failed to run system tray icon: {e}")

    def _on_exit(self, icon, item):
        icon.stop()
        # Shutdown cleanly
        print("Exit via system tray.")
        os._exit(0)

    def _create_circle_image(self, color_name):
        # Create 64x64 transparent image
        img = Image.new('RGBA', (64, 64), color=(0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        # Draw dynamic circle representing indicator status
        d.ellipse([(8, 8), (56, 56)], fill=color_name)
        return img

    def set_state(self, state):
        """Updates the tray icon state/color dynamically."""
        if state not in self.state_colors:
            logger.log_error(f"Invalid tray state requested: {state}")
            return
        self.current_state = state
        if self.icon:
            try:
                new_image = self._create_circle_image(self.state_colors[state])
                self.icon.icon = new_image
            except Exception as e:
                logger.log_error(f"Failed to update tray icon state: {e}")

# Singleton system tray indicator instance
tray_indicator = TrayIndicator()
