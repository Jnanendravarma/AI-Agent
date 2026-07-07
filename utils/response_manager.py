import sys
import os
from voice.speaker import VoiceSpeaker
from utils.logger import logger

class ResponseManager:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(ResponseManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        try:
            self.speaker = VoiceSpeaker()
        except Exception as e:
            logger.log_error(f"ResponseManager failed to initialize VoiceSpeaker: {e}")
            self.speaker = None

        # Setup keyboard hotkey listener for instant Escape-key speech cancellation
        try:
            import keyboard
            keyboard.add_hotkey('esc', self.stop_speaking)
        except Exception as e:
            logger.log_error(f"Failed to bind tactile interruption hotkey: {e}")

        self._initialized = True

    def show_response(self, text: str):
        """Displays the response text on the screen/console."""
        if text:
            print(f"\nAssistant: {text}")

    def speak_response(self, text: str):
        """Synthesizes voice speech for the response text asynchronously."""
        if text and self.speaker:
            from utils.tray_indicator import tray_indicator
            # Briefly set tray to speaking state, then return to sleeping/listening
            tray_indicator.set_state("speaking")
            self.speaker.speak(text)
            
            # Use a quick non-blocking timer to return tray icon to sleeping state after a brief moment 
            # (or let the main loop reset it dynamically)
            def reset_tray():
                import time
                time.sleep(max(1.5, len(text) * 0.08)) # dynamic approximation of speech duration
                if tray_indicator.current_state == "speaking":
                    tray_indicator.set_state("sleeping")
            import threading
            threading.Thread(target=reset_tray, daemon=True).start()

    def respond(self, text: str):
        """Displays the response on screen and speaks it aloud."""
        self.show_response(text)
        self.speak_response(text)

    def stop_speaking(self):
        """Immediately interrupts the active speech synthesis."""
        if self.speaker:
            self.speaker.stop()
            # Reset tray state
            from utils.tray_indicator import tray_indicator
            tray_indicator.set_state("sleeping")

# Singleton response manager instance
response_manager = ResponseManager()
