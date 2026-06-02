import sys
from utils.logger import logger

# Try importing speech_recognition and pyaudio
SPEECH_RECOGNITION_AVAILABLE = False
try:
    import speech_recognition as sr
    SPEECH_RECOGNITION_AVAILABLE = True
except ImportError:
    logger.log_error("speech_recognition library not installed. Falling back to keyboard input mode.")

class VoiceListener:
    def __init__(self):
        self.use_keyboard_fallback = not SPEECH_RECOGNITION_AVAILABLE
        self.recognizer = None
        self.microphone = None

        if SPEECH_RECOGNITION_AVAILABLE:
            try:
                self.recognizer = sr.Recognizer()
                # Adjust threshold dynamically for ambient noise
                self.microphone = sr.Microphone()
                with self.microphone as source:
                    self.recognizer.adjust_for_ambient_noise(source, duration=1)
                print("Voice Recognition initialized successfully.")
            except Exception as e:
                logger.log_error(f"Microphone failed to initialize: {e}. Falling back to keyboard input mode.")
                self.use_keyboard_fallback = True

    def listen(self) -> str:
        """
        Listens for user input.
        If voice recognition is active and operational, uses the microphone.
        Otherwise, falls back to command line text input.
        """
        if self.use_keyboard_fallback:
            try:
                command = input("\nEnter command (Text Mode) >> ").strip()
                return command
            except (KeyboardInterrupt, EOFError):
                return "exit assistant"

        print("\nListening... (Speak your command)")
        try:
            with self.microphone as source:
                audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=5)
            
            print("Processing voice input...")
            command = self.recognizer.recognize_google(audio)
            print(f"Recognized Speech: \"{command}\"")
            return command
        except sr.WaitTimeoutError:
            # Silence timeout, just return empty to continue the loop
            return ""
        except sr.UnknownValueError:
            logger.log_command("Unknown Voice Input", "Failed", "Could not understand audio")
            return ""
        except sr.RequestError as e:
            logger.log_command("Recognition Request", "Failed", f"Google Speech Recognition service error: {e}")
            print("Speech recognition service is down. Switching to keyboard input temporarily.")
            self.use_keyboard_fallback = True
            return ""
        except Exception as e:
            logger.log_error(f"Unexpected listening error: {e}")
            # Try to degrade gracefully to keyboard
            self.use_keyboard_fallback = True
            return ""
