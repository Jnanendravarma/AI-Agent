import os
import json
import datetime
from utils.logger import logger

class MemoryManager:
    def __init__(self, history_file=None):
        if history_file is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            history_file = os.path.join(base_dir, "memory", "conversation_history.json")
            
        self.history_file = history_file
        # Ensure parent folder exists
        os.makedirs(os.path.dirname(self.history_file), exist_ok=True)
        self.history = self.load_history()

    def load_history(self) -> list:
        """Loads conversational history from JSON file."""
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        return data
            except Exception as e:
                logger.log_error(f"Failed to load conversation history: {e}")
        return []

    def save_history(self):
        """Saves current memory buffer to JSON file."""
        try:
            with open(self.history_file, "w", encoding="utf-8") as f:
                json.dump(self.history, f, indent=2)
        except Exception as e:
            logger.log_error(f"Failed to save conversation history: {e}")

    def add_interaction(self, role: str, message: str, context: dict = None):
        """
        Adds a new interaction to conversation history memory.
        Enforces a rolling window limit of the last 20 interactions.
        """
        interaction = {
            "role": role,
            "message": message,
            "timestamp": datetime.datetime.now().isoformat(),
            "context": context or {}
        }
        self.history.append(interaction)
        # Cap memory at the last 20 messages (each role's text counts as an interaction)
        self.history = self.history[-20:]
        self.save_history()

    def get_recent_history(self, limit=20) -> list:
        """Returns the most recent N items in history."""
        return self.history[-limit:]

    def clear_history(self):
        """Clears all entries in conversational history."""
        self.history = []
        self.save_history()
        logger.log_command("Memory System", "Success", "Conversation history cleared.")
