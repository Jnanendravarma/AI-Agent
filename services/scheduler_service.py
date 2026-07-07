import os
import re
import json
import time
import datetime
import threading
from utils.logger import logger

class SchedulerService:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(SchedulerService, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, executor=None):
        if self._initialized:
            return
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.config_path = os.path.join(base_dir, "config", "scheduler_tasks.json")
        self.executor = executor
        self.tasks = []
        self.load_tasks()
        
        # Start background polling thread
        self.running = True
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()
        self._initialized = True

    def load_tasks(self):
        """Loads scheduled tasks from config/scheduler_tasks.json."""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    self.tasks = json.load(f)
            except Exception as e:
                logger.log_error(f"Failed to load scheduler tasks: {e}")
                self.tasks = []
        else:
            self.save_tasks()

    def save_tasks(self):
        """Saves tasks to configuration file."""
        try:
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.tasks, f, indent=2)
        except Exception as e:
            logger.log_error(f"Failed to save scheduler tasks: {e}")

    def add_task(self, command: str, trigger_time: str, task_type: str = "once"):
        """
        Adds a task to the scheduler.
        trigger_time format: 
          - For 'once': 'YYYY-MM-DD HH:MM:SS'
          - For 'daily': 'HH:MM'
        """
        task = {
            "id": str(int(time.time() * 1000)),
            "command": command,
            "trigger_time": trigger_time,
            "type": task_type,
            "active": True
        }
        self.tasks.append(task)
        self.save_tasks()
        logger.log_info(f"Scheduled task added: {command} at {trigger_time} ({task_type})")

    def parse_and_schedule(self, spoken_text: str) -> tuple[bool, str]:
        """
        Parses spoken triggers like:
        - "shutdown pc after 1 hour" / "shutdown after 30 minutes"
        - "open vs code every day at 9 am"
        - "remind me to call Jnanendra tomorrow at 6 pm"
        - "remind me at 8 pm to take a break"
        """
        text_lower = spoken_text.lower().strip()
        
        # 1. Parse relative duration (e.g., "after X hours", "after Y minutes")
        match_after = re.search(r'(?:after|in)\s+(\d+)\s*(hour|minute|second)', text_lower)
        if match_after:
            amount = int(match_after.group(1))
            unit = match_after.group(2)
            
            seconds = amount
            if "hour" in unit:
                seconds = amount * 3600
            elif "minute" in unit:
                seconds = amount * 60
                
            # Extract target command
            clean_cmd = text_lower.replace(match_after.group(0), "").replace("scheduled", "").strip()
            # Clean up introductory words
            clean_cmd = re.sub(r'^(?:run|execute|open|please)\s+', '', clean_cmd)
            
            # If the user specifically said "shutdown pc" or "shutdown"
            if "shutdown" in text_lower:
                clean_cmd = "shutdown pc"
            elif "restart" in text_lower:
                clean_cmd = "restart computer"

            target_dt = datetime.datetime.now() + datetime.timedelta(seconds=seconds)
            trigger_str = target_dt.strftime("%Y-%m-%d %H:%M:%S")
            
            self.add_task(clean_cmd, trigger_str, "once")
            return True, f"I have scheduled '{clean_cmd}' to run in {amount} {unit}s (at {target_dt.strftime('%H:%M:%S')})."

        # 2. Parse daily repeat schedule (e.g., "every day at 9 am", "every day at 21:30")
        match_daily = re.search(r'every\s*day\s*at\s*(\d+)(?::(\d+))?\s*(am|pm)?', text_lower)
        if match_daily:
            hour = int(match_daily.group(1))
            minute = int(match_daily.group(2)) if match_daily.group(2) else 0
            meridiem = match_daily.group(3)
            
            if meridiem:
                if meridiem == "pm" and hour < 12:
                    hour += 12
                elif meridiem == "am" and hour == 12:
                    hour = 0
                    
            time_str = f"{hour:02d}:{minute:02d}"
            clean_cmd = text_lower.replace(match_daily.group(0), "").strip()
            clean_cmd = re.sub(r'^(?:run|execute|open|please)\s+', '', clean_cmd)
            
            self.add_task(clean_cmd, time_str, "daily")
            return True, f"I have scheduled '{clean_cmd}' to run daily at {time_str}."

        # 3. Parse absolute reminder (e.g., "remind me to <action> at <time>")
        match_remind_to = re.search(r'remind\s*me\s*to\s+(.*?)\s+at\s+(\d+)(?::(\d+))?\s*(am|pm)?', text_lower)
        if match_remind_to:
            action = match_remind_to.group(1).strip()
            hour = int(match_remind_to.group(2))
            minute = int(match_remind_to.group(3)) if match_remind_to.group(3) else 0
            meridiem = match_remind_to.group(4)
            
            if meridiem:
                if meridiem == "pm" and hour < 12:
                    hour += 12
                elif meridiem == "am" and hour == 12:
                    hour = 0

            # Determine date: today or tomorrow
            now = datetime.datetime.now()
            target_dt = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if "tomorrow" in text_lower:
                target_dt += datetime.timedelta(days=1)
            elif target_dt < now:
                # If time is already passed today, assume tomorrow
                target_dt += datetime.timedelta(days=1)
                
            trigger_str = target_dt.strftime("%Y-%m-%d %H:%M:%S")
            reminder_cmd = f"remind me {action}"
            
            self.add_task(reminder_cmd, trigger_str, "once")
            return True, f"I have set a reminder to {action} at {target_dt.strftime('%Y-%m-%d %I:%M %p')}."

        # 4. Alternative reminder format (e.g. "remind me at 8 pm to <action>")
        match_remind_at = re.search(r'remind\s*me\s*at\s*(\d+)(?::(\d+))?\s*(am|pm)?\s*(?:to|about)?\s+(.*)', text_lower)
        if match_remind_at:
            hour = int(match_remind_at.group(1))
            minute = int(match_remind_at.group(2)) if match_remind_at.group(2) else 0
            meridiem = match_remind_at.group(3)
            action = match_remind_at.group(4).strip()
            
            if meridiem:
                if meridiem == "pm" and hour < 12:
                    hour += 12
                elif meridiem == "am" and hour == 12:
                    hour = 0

            now = datetime.datetime.now()
            target_dt = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if "tomorrow" in text_lower:
                target_dt += datetime.timedelta(days=1)
            elif target_dt < now:
                target_dt += datetime.timedelta(days=1)
                
            trigger_str = target_dt.strftime("%Y-%m-%d %H:%M:%S")
            reminder_cmd = f"remind me {action}"
            
            self.add_task(reminder_cmd, trigger_str, "once")
            return True, f"I have set a reminder to {action} at {target_dt.strftime('%Y-%m-%d %I:%M %p')}."

        return False, ""

    def _run_loop(self):
        """Background daemon loops and executes tasks when their trigger time matches."""
        while self.running:
            try:
                now = datetime.datetime.now()
                now_str = now.strftime("%Y-%m-%d %H:%M:%S")
                time_str = now.strftime("%H:%M")
                
                tasks_modified = False
                
                for task in self.tasks:
                    if not task.get("active", False):
                        continue
                        
                    is_due = False
                    
                    if task["type"] == "once":
                        # Compare date-time string
                        trigger_dt = datetime.datetime.strptime(task["trigger_time"], "%Y-%m-%d %H:%M:%S")
                        if now >= trigger_dt:
                            is_due = True
                            task["active"] = False # Run once only
                            tasks_modified = True
                            
                    elif task["type"] == "daily":
                        # Compare time HH:MM, and check if already run this minute
                        if time_str == task["trigger_time"]:
                            # Ensure we don't double fire in the same minute
                            last_run = task.get("last_run_date", "")
                            today_str = now.strftime("%Y-%m-%d")
                            if last_run != today_str:
                                is_due = True
                                task["last_run_date"] = today_str
                                tasks_modified = True

                    if is_due:
                        # Execute command
                        threading.Thread(target=self._execute_task_command, args=(task["command"],), daemon=True).start()
                
                if tasks_modified:
                    self.save_tasks()
                    
            except Exception as e:
                logger.log_error(f"Error in scheduler running loop: {e}")
                
            time.sleep(1)

    def _execute_task_command(self, command: str):
        """Helper to run the command via executor loop."""
        try:
            # If the command starts with "remind me "
            if command.startswith("remind me "):
                reminder = command.replace("remind me ", "").strip()
                from utils.response_manager import response_manager
                response_manager.respond(f"Reminder: {reminder.capitalize()}")
                return

            # Resolve executor dynamically
            if self.executor is None:
                from engine.command_executor import CommandExecutor
                self.executor = CommandExecutor()
            
            logger.log_info(f"Scheduler executing scheduled command: '{command}'")
            self.executor.execute(command)
        except Exception as e:
            logger.log_error(f"Scheduler failed to run task command '{command}': {e}")

    def stop(self):
        """Stops the scheduler loop."""
        self.running = False
