import os
import datetime

class AssistantLogger:
    def __init__(self, log_dir="logs", log_filename="assistant.log"):
        self.log_dir = log_dir
        self.log_path = os.path.join(self.log_dir, log_filename)
        
        # Ensure log directory exists
        os.makedirs(self.log_dir, exist_ok=True)
        
    def log_command(self, command: str, status: str, details: str = None):
        """
        Logs the command and execution status in the specified format:
        [HH:MM:SS]
        User Command: <Command>
        Status: <Status>
        """
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        
        log_entry = f"[{timestamp}]\n"
        log_entry += f"User Command: {command}\n"
        log_entry += f"Status: {status}\n"
        if details:
            log_entry += f"Details: {details}\n"
        log_entry += "\n"  # Empty line separator as required
        
        # Write to file
        try:
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(log_entry)
        except Exception as e:
            print(f"Failed to write to log file: {e}")
            
        # Print to console for visibility
        console_details = f" ({details})" if details else ""
        print(f"[{timestamp}] Command: '{command}' | Status: {status}{console_details}")

    def log_interaction(self, command: str, intent: str, result: str, gemini_usage: str, response_time: float, errors: str = None):
        """
        Logs detailed interaction metrics including intent, Gemini usage, and response time.
        """
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        log_entry = f"[{timestamp}]\n"
        log_entry += f"User Command: {command}\n"
        log_entry += f"Intent Detected: {intent}\n"
        log_entry += f"Execution Result: {result}\n"
        log_entry += f"Gemini Usage: {gemini_usage}\n"
        log_entry += f"Response Time: {response_time:.4f}s\n"
        if errors:
            log_entry += f"Errors: {errors}\n"
        log_entry += "\n"
        
        try:
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(log_entry)
        except Exception as e:
            print(f"Failed to write to log file: {e}")

    def log_error(self, message: str):
        """Logs general errors."""
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] ERROR: {message}\n\n"
        try:
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(log_entry)
        except Exception as e:
            pass
        print(f"[{timestamp}] ERROR: {message}")

    def log_info(self, message: str):
        """Logs general information messages."""
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] INFO: {message}\n\n"
        try:
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(log_entry)
        except Exception:
            pass
        print(f"[{timestamp}] INFO: {message}")

# Singleton logger instance
logger = AssistantLogger()

