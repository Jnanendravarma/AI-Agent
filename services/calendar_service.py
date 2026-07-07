import os
import json
import re
import datetime
from utils.logger import logger

class CalendarService:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(CalendarService, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.config_path = os.path.join(base_dir, "config", "calendar.json")
        self.events = []
        self.load_events()
        self._initialized = True

    def load_events(self):
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    self.events = json.load(f)
            except Exception as e:
                logger.log_error(f"Failed to load calendar events: {e}")
                self.events = []
        else:
            self.save_events()

    def save_events(self):
        try:
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.events, f, indent=2)
        except Exception as e:
            logger.log_error(f"Failed to save calendar: {e}")

    def add_event(self, command: str) -> tuple[bool, str]:
        """
        Parses commands like:
        - "create meeting with Team tomorrow at 10 AM"
        - "schedule appointment Dentist on 2026-07-15 at 14:30"
        """
        cmd_lower = command.lower().strip()
        
        # Default target date & time
        now = datetime.datetime.now()
        target_dt = now
        
        # 1. Parse date (tomorrow, today, or explicit date YYYY-MM-DD)
        is_tomorrow = "tomorrow" in cmd_lower
        explicit_date = re.search(r'on\s+(\d{4}-\d{2}-\d{2})', cmd_lower)
        
        if is_tomorrow:
            target_dt += datetime.timedelta(days=1)
        elif explicit_date:
            try:
                dt_part = datetime.datetime.strptime(explicit_date.group(1), "%Y-%m-%d")
                target_dt = target_dt.replace(year=dt_part.year, month=dt_part.month, day=dt_part.day)
            except Exception:
                return False, "Invalid date format. Please use YYYY-MM-DD."

        # 2. Parse time (e.g., at 10 am, at 14:30, at 8 pm)
        match_time = re.search(r'at\s+(\d+)(?::(\d+))?\s*(am|pm)?', cmd_lower)
        if match_time:
            hour = int(match_time.group(1))
            minute = int(match_time.group(2)) if match_time.group(2) else 0
            meridiem = match_time.group(3)
            
            if meridiem:
                if meridiem == "pm" and hour < 12:
                    hour += 12
                elif meridiem == "am" and hour == 12:
                    hour = 0
            target_dt = target_dt.replace(hour=hour, minute=minute, second=0, microsecond=0)
        else:
            # Default to next hour if time not specified
            target_dt = (now + datetime.timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)

        # 3. Extract title
        title = "Meeting"
        # Extract title by stripping off time keywords
        title_raw = command
        # Strip prefixes
        title_raw = re.sub(r'^(?:create|schedule|add|new)\s+(?:meeting|appointment|event)\s+(?:with|for)?\s*', '', title_raw, flags=re.IGNORECASE)
        # Strip time terms
        title_raw = re.sub(r'\s+(?:at|on|tomorrow|today).*$', '', title_raw, flags=re.IGNORECASE).strip()
        if title_raw:
            title = title_raw
            
        event = {
            "title": title,
            "datetime": target_dt.strftime("%Y-%m-%d %H:%M:%S")
        }
        self.events.append(event)
        # Keep events sorted chronologically
        self.events.sort(key=lambda x: x["datetime"])
        self.save_events()
        
        return True, f"I have scheduled '{title}' for {target_dt.strftime('%B %d, %Y at %I:%M %p')}."

    def list_events(self, command: str) -> tuple[bool, str]:
        """Lists events scheduled for today or all upcoming events."""
        cmd_lower = command.lower().strip()
        now = datetime.datetime.now()
        today_str = now.strftime("%Y-%m-%d")
        
        filtered = []
        is_today_only = "today" in cmd_lower or "schedule" in cmd_lower and "all" not in cmd_lower
        
        for e in self.events:
            dt = datetime.datetime.strptime(e["datetime"], "%Y-%m-%d %H:%M:%S")
            # If past event, skip
            if dt < now.replace(hour=0, minute=0, second=0):
                continue
            if is_today_only:
                if dt.strftime("%Y-%m-%d") == today_str:
                    filtered.append(e)
            else:
                filtered.append(e)

        if not filtered:
            period = "today" if is_today_only else "the upcoming period"
            return True, f"You have no meetings scheduled for {period}."

        lines = []
        for e in filtered:
            dt = datetime.datetime.strptime(e["datetime"], "%Y-%m-%d %H:%M:%S")
            time_lbl = dt.strftime("%I:%M %p")
            if not is_today_only:
                time_lbl = dt.strftime("%b %d at %I:%M %p")
            lines.append(f"'{e['title']}' at {time_lbl}")

        desc = "today's schedule includes" if is_today_only else "your upcoming schedule includes"
        return True, f"Yes, {desc}: " + "; and ".join(lines)
