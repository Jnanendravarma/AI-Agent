import os
import json
import time
import re
from plugins.base_plugin import BasePlugin
from utils.logger import logger

class NotesPlugin(BasePlugin):
    def __init__(self, executor):
        super().__init__(executor)
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.notes_path = os.path.join(base_dir, "config", "notes.json")

    def get_keywords(self) -> list[str]:
        return ["take note", "save note", "write note", "show notes", "list notes", "clear notes", "delete note"]

    def execute(self, command: str) -> tuple[bool, str]:
        cmd_lower = command.lower().strip()
        
        # Load notes
        notes = []
        if os.path.exists(self.notes_path):
            try:
                with open(self.notes_path, "r", encoding="utf-8") as f:
                    notes = json.load(f)
            except Exception as e:
                logger.log_error(f"Failed to load notes: {e}")

        # 1. Show / List Notes
        if cmd_lower in ["show notes", "list notes"]:
            if not notes:
                return True, "You don't have any saved notes."
            lines = []
            for i, note in enumerate(notes, 1):
                lines.append(f"{i}. {note['content']} (saved {note['date']})")
            return True, "Your saved notes are: " + "; and ".join(lines)

        # 2. Clear Notes
        if cmd_lower == "clear notes":
            notes = []
            self._save(notes)
            return True, "All notes cleared successfully."

        # 3. Delete specific note (e.g., "delete note 1")
        match_del = re.search(r'delete\s*note\s*(\d+)', cmd_lower)
        if match_del:
            idx = int(match_del.group(1)) - 1
            if 0 <= idx < len(notes):
                removed = notes.pop(idx)
                self._save(notes)
                return True, f"Deleted note: '{removed['content']}'"
            else:
                return False, f"Invalid note number. You have {len(notes)} notes."

        # 4. Take / Save Note (e.g. "take note buy groceries")
        note_text = ""
        for trigger in ["take note", "save note", "write note"]:
            if trigger in cmd_lower:
                parts = command.split(command.lower().split(trigger)[0] + trigger)
                if len(parts) > 1:
                    note_text = parts[1].strip()
                    break

        if not note_text:
            # Fallback extraction
            note_text = command.strip()

        # Clean introductory punctuation
        note_text = re.sub(r'^[,\s!?.-]+', '', note_text).strip()
        
        if not note_text or note_text.lower() in ["note", "notes"]:
            return False, "What note would you like me to save?"

        import datetime
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        notes.append({
            "content": note_text,
            "date": timestamp
        })
        self._save(notes)
        return True, f"Saved note: '{note_text}'"

    def _save(self, notes):
        try:
            os.makedirs(os.path.dirname(self.notes_path), exist_ok=True)
            with open(self.notes_path, "w", encoding="utf-8") as f:
                json.dump(notes, f, indent=2)
        except Exception as e:
            logger.log_error(f"Failed to save notes file: {e}")
