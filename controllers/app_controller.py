import os
import subprocess
from utils.logger import logger

class AppController:
    @staticmethod
    def open_app(command_or_path: str) -> bool:
        """
        Launches an application either by an OS command or an absolute path.
        """
        try:
            # Check if it looks like an absolute path
            if os.path.isabs(command_or_path):
                if os.path.exists(command_or_path):
                    # Use os.startfile on Windows for robust execution (similar to double-clicking)
                    os.startfile(command_or_path)
                    return True
                else:
                    logger.log_error(f"Path does not exist: {command_or_path}")
                    return False
            
            # Run OS command using subprocess with shell=True on Windows
            # e.g., 'start chrome', 'notepad', 'calc'
            subprocess.Popen(command_or_path, shell=True)
            return True
        except Exception as e:
            logger.log_error(f"Failed to open application '{command_or_path}': {e}")
            return False

    @staticmethod
    def is_app_running(process_name: str) -> bool:
        """
        Checks if an application process is running using psutil.
        """
        try:
            import psutil
            for proc in psutil.process_iter(['name']):
                if proc.info['name'] and proc.info['name'].lower() == process_name.lower():
                    return True
            return False
        except ImportError:
            logger.log_error("psutil not available to check running status.")
            return False
        except Exception as e:
            logger.log_error(f"Error checking app status for {process_name}: {e}")
            return False
