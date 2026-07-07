import os
import re
import json
import threading
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
        self.sapi_speaker = None
        self.active_synthesizer = None
        self.speaking_lock = threading.Lock()

        # Load dynamic settings
        self.rate = 1.0     # multiplier, e.g. 1.0 (normal), 1.2 (fast), 0.8 (slow)
        self.volume = 1.0   # 0.0 to 1.0
        self.gender = "female"
        self.load_voice_config()

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

        # 3. Initialize standard SAPI5 or pyttsx3 fallback
        if not self.azure_client and not self.eleven_client:
            try:
                import pythoncom
                pythoncom.CoInitialize()
                import win32com.client
                self.sapi_speaker = win32com.client.Dispatch("SAPI.SpVoice")
                logger.log_command("Voice Speaker init", "Success", "Direct SAPI5 async speaker initialized.")
            except Exception as e:
                logger.log_error(f"Failed to initialize direct SAPI5 COM: {e}. Trying pyttsx3 fallback...")
                if PYTTSX3_AVAILABLE:
                    try:
                        self.local_engine = pyttsx3.init()
                        logger.log_command("Voice Speaker init", "Success", "Local pyttsx3 fallback active.")
                    except Exception as ex:
                        logger.log_error(f"Local pyttsx3 init failed: {ex}")

    def load_voice_config(self):
        """Loads volume, speed, and gender settings from the preferences manager."""
        try:
            from utils.preferences_manager import preferences_manager
            self.rate = float(preferences_manager.get("speech_rate", 1.0))
            self.volume = float(preferences_manager.get("volume", 1.0))
            self.gender = preferences_manager.get("gender", "female").lower()
        except Exception as e:
            logger.log_error(f"Failed to load voice preferences: {e}")

    def apply_local_engine_settings(self):
        """Configures rate, volume, and gender on the pyttsx3 local engine."""
        if not self.local_engine:
            return
        try:
            self.local_engine.setProperty("rate", int(200 * self.rate))
            self.local_engine.setProperty("volume", self.volume)
            voices = self.local_engine.getProperty("voices")
            selected_voice = None
            if self.gender == "female":
                for voice in voices:
                    if hasattr(voice, "gender") and voice.gender == "female":
                        selected_voice = voice.id
                        break
                    elif any(kw in voice.name.lower() for kw in ["zira", "female", "harita", "kalpana"]):
                        selected_voice = voice.id
                        break
            if not selected_voice and voices:
                selected_voice = voices[1].id if len(voices) > 1 else voices[0].id
            if selected_voice:
                self.local_engine.setProperty("voice", selected_voice)
        except Exception as e:
            logger.log_error(f"Failed to apply local engine settings: {e}")

    def detect_language(self, text: str) -> str:
        """Helper to classify language based on unicode ranges or transliterated keywords."""
        text_lower = text.lower()
        if re.search(r"[\u0c00-\u0c7f]", text):
            return "te"
        if re.search(r"[\u0900-\u097f]", text):
            return "hi"
        telugu_keywords = ["cheyyi", "open chey", "chastna", "pettuko", "chesthunna", "thagginchu", "penchu", "chesanu", "chesanu"]
        if any(w in text_lower for w in telugu_keywords):
            return "te"
        hindi_keywords = ["karo", "kholo", "band kar", "rakho", "raha hoon", "kar raha", "kar diya"]
        if any(w in text_lower for w in hindi_keywords):
            return "hi"
        return "en"

    def speak(self, text: str):
        """
        Speaks the given text asynchronously using the best available voice.
        Console output is handled separately by the ResponseManager.
        """
        if not text:
            return

        # Reload settings dynamically
        self.load_voice_config()
        lang = self.detect_language(text)

        # 1. Speak using Azure Speech SDK
        if self.azure_client:
            def _speak_azure():
                try:
                    voice_name = "en-US-JennyNeural"
                    if lang == "te":
                        voice_name = "te-IN-ShrutiNeural"
                    elif lang == "hi":
                        voice_name = "hi-IN-SwaraNeural"
                    elif lang == "en":
                        voice_name = "en-IN-NeerjaNeural"

                    speech_config = speechsdk.SpeechConfig(subscription=self.azure_key, region=self.azure_region)
                    audio_config = speechsdk.audio.AudioOutputConfig(use_default_speaker=True)
                    synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=audio_config)
                    self.active_synthesizer = synthesizer
                    
                    rate_pct = f"{int((self.rate - 1.0) * 100):+d}%"
                    volume_pct = f"{int((self.volume - 1.0) * 100):+d}%"
                    
                    ssml = f"""<speak version='1.0' xmlns='http://www.w3.org/2001/10/synthesis' xml:lang='{lang}'>
  <voice name='{voice_name}'>
    <prosody rate='{rate_pct}' volume='{volume_pct}'>
      {text}
    </prosody>
  </voice>
</speak>"""
                    synthesizer.speak_ssml_async(ssml)
                except Exception as e:
                    logger.log_error(f"Azure neural text synthesis failed: {e}")
            threading.Thread(target=_speak_azure, daemon=True).start()
            return

        # 2. Speak using ElevenLabs API
        if self.eleven_client:
            def _speak_eleven():
                try:
                    audio = self.eleven_client.generate(
                        text=text,
                        voice=self.eleven_voice_id,
                        model="eleven_multilingual_v2"
                    )
                    play(audio)
                except Exception as e:
                    logger.log_error(f"ElevenLabs text synthesis failed: {e}")
            threading.Thread(target=_speak_eleven, daemon=True).start()
            return

        # 3. Speak using Direct SAPI5 (Non-blocking async)
        if self.sapi_speaker:
            def _speak_sapi():
                with self.speaking_lock:
                    try:
                        import pythoncom
                        pythoncom.CoInitialize()
                        self.sapi_speaker.Volume = int(self.volume * 100)
                        self.sapi_speaker.Rate = int((self.rate - 1.0) * 10)
                        
                        voices = self.sapi_speaker.GetVoices()
                        selected = None
                        for i in range(voices.Count):
                            desc = voices.Item(i).GetDescription().lower()
                            if "female" in desc or "zira" in desc or "harita" in desc:
                                selected = voices.Item(i)
                                break
                        if selected:
                            self.sapi_speaker.Voice = selected
                        # Speak with SVSFlagsAsync = 1
                        self.sapi_speaker.Speak(text, 1)
                    except Exception as e:
                        logger.log_error(f"Direct SAPI5 speaking failed: {e}")
            threading.Thread(target=_speak_sapi, daemon=True).start()
            return

        # 4. Speak using pyttsx3 Local Engine (Fallback in thread)
        if self.local_engine:
            def _speak_fallback():
                with self.speaking_lock:
                    try:
                        self.apply_local_engine_settings()
                        self.local_engine.say(text)
                        self.local_engine.runAndWait()
                    except Exception as e:
                        logger.log_error(f"Local pyttsx3 speaking failed: {e}")
            threading.Thread(target=_speak_fallback, daemon=True).start()
            return

    def stop(self):
        """Immediately stops any running or queued voice playback."""
        logger.log_info("Interruption triggered: stopping speaker output.")
        # Stop SAPI5
        if self.sapi_speaker:
            try:
                # SVSFPurgeBeforeSpeak = 2
                self.sapi_speaker.Speak("", 2)
            except Exception as e:
                logger.log_error(f"Failed to cancel SAPI5 speech: {e}")
        # Stop Azure Synthesizer
        if self.active_synthesizer:
            try:
                self.active_synthesizer.stop_speaking_async()
            except Exception as e:
                logger.log_error(f"Failed to cancel Azure speech: {e}")
        # Stop pyttsx3
        if self.local_engine:
            try:
                self.local_engine.stop()
            except Exception as e:
                logger.log_error(f"Failed to cancel pyttsx3 speech: {e}")
