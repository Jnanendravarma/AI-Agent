import os
import re
from utils.logger import logger
from dotenv import load_dotenv

# Try importing dependencies
AZURE_SPEECH_AVAILABLE = False
try:
    import azure.cognitiveservices.speech as speechsdk
    AZURE_SPEECH_AVAILABLE = True
except ImportError:
    pass

ELEVENLABS_AVAILABLE = False
try:
    from elevenlabs.client import ElevenLabs
    from elevenlabs import play
    ELEVENLABS_AVAILABLE = True
except ImportError:
    pass

PYTTSX3_AVAILABLE = False
try:
    import pyttsx3
    PYTTSX3_AVAILABLE = True
except ImportError:
    pass

load_dotenv()

class VoiceSpeaker:
    def __init__(self):
        self.azure_key = os.getenv("AZURE_SPEECH_KEY") or os.getenv("SPEECH_KEY")
        self.azure_region = os.getenv("AZURE_SPEECH_REGION") or os.getenv("SPEECH_REGION")
        self.eleven_key = os.getenv("ELEVENLABS_API_KEY")
        self.eleven_voice_id = os.getenv("ELEVENLABS_VOICE_ID", "Rachel")
        
        self.azure_client = None
        self.eleven_client = None
        self.local_engine = None

        # 1. Initialize Azure Neural Voice
        if AZURE_SPEECH_AVAILABLE and self.azure_key and self.azure_region:
            try:
                speech_config = speechsdk.SpeechConfig(subscription=self.azure_key, region=self.azure_region)
                self.azure_client = speech_config
                logger.log_command("Voice Speaker init", "Success", "Azure Neural Voice system active.")
            except Exception as e:
                logger.log_error(f"Failed to configure Azure Neural Voice: {e}")

        # 2. Initialize ElevenLabs
        if not self.azure_client and ELEVENLABS_AVAILABLE and self.eleven_key:
            try:
                self.eleven_client = ElevenLabs(api_key=self.eleven_key)
                logger.log_command("Voice Speaker init", "Success", "ElevenLabs Multilingual Voice active.")
            except Exception as e:
                logger.log_error(f"Failed to initialize ElevenLabs client: {e}")

        # 3. Fallback local voice
        if not self.azure_client and not self.eleven_client and PYTTSX3_AVAILABLE:
            try:
                self.local_engine = pyttsx3.init()
                self.local_engine.setProperty("rate", 185)
                self.local_engine.setProperty("volume", 0.9)
                voices = self.local_engine.getProperty("voices")
                if voices:
                    if len(voices) > 1:
                        self.local_engine.setProperty("voice", voices[1].id)
                    else:
                        self.local_engine.setProperty("voice", voices[0].id)
                logger.log_command("Voice Speaker init", "Success", "Local pyttsx3 fallback active.")
            except Exception as e:
                logger.log_error(f"Local pyttsx3 init failed: {e}")

    def detect_language(self, text: str) -> str:
        """Helper to classify language based on unicode ranges (Telugu and Hindi)."""
        # Telugu Unicode Range
        if re.search(r"[\u0c00-\u0c7f]", text):
            return "te"
        # Hindi/Devanagari Unicode Range
        if re.search(r"[\u0900-\u097f]", text):
            return "hi"
        return "en"

    def speak(self, text: str):
        """
        Speaks the given text using the best available premium neural or local fallback voice,
        while maintaining console printouts.
        """
        print(f"Assistant: {text}")
        if not text:
            return

        lang = self.detect_language(text)

        # 1. Speak using Azure Speech SDK
        if self.azure_client:
            try:
                voice_name = "en-US-JennyNeural"
                if lang == "te":
                    voice_name = "te-IN-ShrutiNeural"
                elif lang == "hi":
                    voice_name = "hi-IN-SwaraNeural"
                elif lang == "en":
                    # For Indian English or mixed Hinglish/Telglish phrases
                    voice_name = "en-IN-NeerjaNeural"

                speech_config = speechsdk.SpeechConfig(subscription=self.azure_key, region=self.azure_region)
                speech_config.speech_synthesis_voice_name = voice_name
                audio_config = speechsdk.audio.AudioOutputConfig(use_default_speaker=True)
                synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=audio_config)
                synthesizer.speak_text_async(text).get()
                return
            except Exception as e:
                logger.log_error(f"Azure neural text synthesis failed: {e}. Falling back...")

        # 2. Speak using ElevenLabs API
        if self.eleven_client:
            try:
                audio = self.eleven_client.generate(
                    text=text,
                    voice=self.eleven_voice_id,
                    model="eleven_multilingual_v2"
                )
                play(audio)
                return
            except Exception as e:
                logger.log_error(f"ElevenLabs text synthesis failed: {e}. Falling back...")

        # 3. Speak using pyttsx3 Local Engine
        if self.local_engine:
            try:
                self.local_engine.say(text)
                self.local_engine.runAndWait()
                return
            except Exception as e:
                logger.log_error(f"Local pyttsx3 text synthesis failed: {e}")
