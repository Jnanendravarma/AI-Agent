from utils.logger import logger

# Try importing pyttsx3
PYTTSX3_AVAILABLE = False
try:
    import pyttsx3
    PYTTSX3_AVAILABLE = True
except ImportError:
    logger.log_error("pyttsx3 library not installed. Assistant speech will only print to screen.")

class VoiceSpeaker:
    def __init__(self):
        self.engine = None
        if PYTTSX3_AVAILABLE:
            try:
                # Initialize SAPI5 on Windows
                self.engine = pyttsx3.init()
                # Set speed/rate slightly slower for premium clear voice
                self.engine.setProperty("rate", 185)
                # Adjust volume
                self.engine.setProperty("volume", 0.9)
                
                # Check voices and select a default one if available
                voices = self.engine.getProperty("voices")
                if voices:
                    # Prefer Zira (usually index 1, female) or default
                    if len(voices) > 1:
                        self.engine.setProperty("voice", voices[1].id)
                    else:
                        self.engine.setProperty("voice", voices[0].id)
            except Exception as e:
                logger.log_error(f"pyttsx3 initialization failed: {e}. Text-to-speech is disabled.")
                self.engine = None

    def speak(self, text: str):
        """
        Speaks the given text using text-to-speech.
        Also prints to the console for complete clarity.
        """
        print(f"Assistant: {text}")
        if self.engine:
            try:
                self.engine.say(text)
                self.engine.runAndWait()
            except Exception as e:
                logger.log_error(f"Failed to speak audio: {e}")
