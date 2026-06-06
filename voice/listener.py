import sys
import os
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

    def wait_for_wake_word(self) -> bool:
        """
        Listens continuously in low-resource loop for wake words: 'hey buddy' or 'hey mitra'.
        Bypasses and returns True immediately if in keyboard fallback mode.
        """
        if self.use_keyboard_fallback or not self.wake_word_enabled:
            return True

        print("\n[Idle Mode] Listening for wake word ('Hey buddy' or 'Hey mitra')...")
        while True:
            try:
                with self.microphone as source:
                    # short timeout for responsive looping
                    audio = self.recognizer.listen(source, timeout=3, phrase_time_limit=3)
                
                phrase = self.recognizer.recognize_google(audio).lower().strip()
                if "hey buddy" in phrase or "hey mitra" in phrase or "mitra" in phrase:
                    print(f"Wake word detected: '{phrase}'")
                    return True
            except sr.WaitTimeoutError:
                # Silence timeout, continue waiting
                continue
            except sr.UnknownValueError:
                # Unrecognized sounds, continue waiting
                continue
            except sr.RequestError as e:
                logger.log_error(f"Speech recognition service issue during wake word: {e}")
                print("Switching to keyboard fallback temporarily.")
                self.use_keyboard_fallback = True
                return True
            except Exception as e:
                logger.log_error(f"Error in wake word listener: {e}")
                return True

    def listen(self) -> str:
        """
        Listens for user input command.
        Uses microphone if voice recognition is operational; otherwise falls back to keyboard.
        """
        if self.use_keyboard_fallback:
            try:
                command = input("\nEnter command (Text Mode) >> ").strip()
                return command
            except (KeyboardInterrupt, EOFError):
                return "exit assistant"

        print("\nActive Mode: Listening for command...")
        try:
            with self.microphone as source:
                audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=5)
            
            print("Processing voice input...")
            command = self.recognizer.recognize_google(audio)
            print(f"Recognized Command: \"{command}\"")
            return command
        except sr.WaitTimeoutError:
            print("Listening timed out. Returning to idle mode.")
            return ""
        except sr.UnknownValueError:
            logger.log_command("Unknown Voice Input", "Failed", "Could not understand audio")
            return ""
        except sr.RequestError as e:
            logger.log_command("Recognition Request", "Failed", f"Google Speech Recognition error: {e}")
            print("Speech service down. Switching to keyboard input temporarily.")
            self.use_keyboard_fallback = True
            return ""
        except Exception as e:
            logger.log_error(f"Unexpected error in active listener: {e}")
            self.use_keyboard_fallback = True
            return ""
