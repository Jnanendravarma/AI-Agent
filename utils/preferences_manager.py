import os
import json
from utils.logger import logger

class PreferencesManager:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(PreferencesManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.config_path = os.path.join(base_dir, "config", "user_preferences.json")
        self.preferences = {
            "language": "en",
            "username": "Jnanendra",
            "speech_rate": 1.0,
            "volume": 1.0,
            "theme": "dark",
            "favorite_browser": "chrome",
            "preferred_ide": "vscode",
            "favorite_player": "spotify",
            "coding_folder": "",
            "learned_assets": {}
        }
        self.load_preferences()
        self._initialized = True

    def load_preferences(self):
        """Loads preferences from user_preferences.json file."""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.preferences.update(data)
            except Exception as e:
                logger.log_error(f"Failed to load user preferences: {e}")
        else:
            self.save_preferences()

    def save_preferences(self):
        """Saves current preferences dictionary to user_preferences.json."""
        try:
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.preferences, f, indent=2)
        except Exception as e:
            logger.log_error(f"Failed to save user preferences: {e}")

    def get(self, key, default=None):
        """Gets a preference value."""
        return self.preferences.get(key, default)

    def set(self, key, value):
        """Sets a preference value and saves it."""
        self.preferences[key] = value
        self.save_preferences()
        # If voice settings were updated, we also update the voice_config.json for compatibility
        if key in ["speech_rate", "volume", "language"]:
            self._sync_voice_config()

    def _sync_voice_config(self):
        """Synchronizes preferences to standard voice_config.json."""
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        voice_config_path = os.path.join(base_dir, "config", "voice_config.json")
        try:
            config = {
                "rate": self.get("speech_rate", 1.0),
                "volume": self.get("volume", 1.0),
                "gender": "female"  # defaults to female
            }
            with open(voice_config_path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            logger.log_error(f"Failed to sync voice config: {e}")

# Singleton preferences manager instance
preferences_manager = PreferencesManager()
