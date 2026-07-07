import sys
import os
import re
from utils.logger import logger
from dotenv import load_dotenv

# Try importing speech_recognition and pyaudio
SPEECH_RECOGNITION_AVAILABLE = False
try:
    import speech_recognition as sr
    SPEECH_RECOGNITION_AVAILABLE = True
except ImportError:
    logger.log_error("speech_recognition library not installed. Falling back to keyboard input mode.")

load_dotenv()

class VoiceListener:
    def __init__(self):
        self.use_keyboard_fallback = not SPEECH_RECOGNITION_AVAILABLE
        self.recognizer = None
        self.microphone = None
        self.wake_word_enabled = os.getenv("WAKE_WORD_ENABLED", "true").lower() == "true"

        if SPEECH_RECOGNITION_AVAILABLE:
            try:
                self.recognizer = sr.Recognizer()
                self.microphone = sr.Microphone()
                with self.microphone as source:
                    self.recognizer.adjust_for_ambient_noise(source, duration=1)
                print("Voice Recognition initialized successfully.")
            except Exception as e:
                logger.log_error(f"Microphone failed to initialize: {e}. Falling back to keyboard input mode.")
                self.use_keyboard_fallback = True

    def wait_for_wake_word(self) -> tuple[bool, str]:
        """
        Listens continuously in low-resource loop for wake words: 'hey buddy' or 'hey mitra'.
        Returns a tuple of (wake_word_detected: bool, remaining_command_text: str).
        """
        if self.use_keyboard_fallback or not self.wake_word_enabled:
            return True, ""

        print("\n[Idle Mode] Listening for wake word ('Hey buddy' or 'Hey mitra')...")
        while True:
            try:
                from utils.tray_indicator import tray_indicator
                tray_indicator.set_state("sleeping") # Gray when sleeping/idle
                
                with self.microphone as source:
                    # Bounded timeout for responsive loop, but larger phrase limit to capture trailing command
                    audio = self.recognizer.listen(source, timeout=3, phrase_time_limit=8)
                
                tray_indicator.set_state("processing") # Blue when processing audio
                phrase = self.recognizer.recognize_google(audio).strip()
                phrase_lower = phrase.lower()
                
                wake_words = ["hey buddy", "hey mitra", "mitra", "buddy"]
                for wake in wake_words:
                    if wake in phrase_lower:
                        idx = phrase_lower.find(wake)
                        remaining = phrase[idx + len(wake):].strip()
                        # Strip common leading punctuation
                        remaining = re.sub(r'^[,\s!?.-]+', '', remaining).strip()
                        print(f"Wake word detected: '{phrase}'")
                        return True, remaining
            except sr.WaitTimeoutError:
                continue
            except sr.UnknownValueError:
                continue
            except sr.RequestError as e:
                logger.log_error(f"Speech recognition service issue during wake word: {e}")
                print("Switching to keyboard fallback temporarily.")
                self.use_keyboard_fallback = True
                return True, ""
            except Exception as e:
                logger.log_error(f"Error in wake word listener: {e}")
                return True, ""

    def listen(self) -> str:
        """
        Listens for user input command.
        Uses microphone if voice recognition is operational; otherwise falls back to keyboard.
        """
        from utils.tray_indicator import tray_indicator
        
        if self.use_keyboard_fallback:
            try:
                tray_indicator.set_state("listening") # Green when listening
                command = input("\nEnter command (Text Mode) >> ").strip()
                tray_indicator.set_state("processing") # Blue when processing
                return command
            except (KeyboardInterrupt, EOFError):
                return "exit assistant"

        print("\nActive Mode: Listening for command...")
        try:
            tray_indicator.set_state("listening") # Green when listening
            with self.microphone as source:
                audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=8)
            
            tray_indicator.set_state("processing") # Blue when processing
            print("Processing voice input...")
            command = self.recognizer.recognize_google(audio).strip()
            print(f"Recognized Command: \"{command}\"")

            # Check for direct voice-interrupt stop keywords
            cmd_lower = command.lower().strip()
            if cmd_lower in ["stop", "enough", "cancel", "silence", "stop talking"]:
                from utils.response_manager import response_manager
                response_manager.stop_speaking()
                print("[Speech Synthesis Interrupted via Voice Command]")
                return ""

            return command
        except sr.WaitTimeoutError:
            print("Listening timed out. Returning to idle mode.")
            tray_indicator.set_state("sleeping")
            return ""
        except sr.UnknownValueError:
            logger.log_command("Unknown Voice Input", "Failed", "Could not understand audio")
            tray_indicator.set_state("sleeping")
            return ""
        except sr.RequestError as e:
            logger.log_command("Recognition Request", "Failed", f"Google Speech Recognition error: {e}")
            print("Speech service down. Switching to keyboard input temporarily.")
            self.use_keyboard_fallback = True
            tray_indicator.set_state("sleeping")
            return ""
        except Exception as e:
            logger.log_error(f"Unexpected error in active listener: {e}")
            self.use_keyboard_fallback = True
            tray_indicator.set_state("sleeping")
            return ""
