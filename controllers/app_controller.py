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

    # --- Dedicated handlers for specific applications to avoid overlapping logic ---

    @staticmethod
    def open_chrome() -> bool:
        """Explicit handler to launch Google Chrome."""
        logger.log_command("open_chrome", "Success", "Executing dedicated Chrome launch")
        return AppController.open_app("start chrome")

    @staticmethod
    def close_chrome() -> bool:
        """Explicit handler to terminate all Google Chrome processes."""
        from controllers.process_manager import ProcessManager
        logger.log_command("close_chrome", "Success", "Executing dedicated Chrome close")
        return ProcessManager.kill_process_by_name("chrome.exe")

    @staticmethod
    def open_edge() -> bool:
        """Explicit handler to launch Microsoft Edge."""
        logger.log_command("open_edge", "Success", "Executing dedicated Edge launch")
        return AppController.open_app("start msedge")

    @staticmethod
    def close_edge() -> bool:
        """Explicit handler to terminate all Microsoft Edge processes."""
        from controllers.process_manager import ProcessManager
        logger.log_command("close_edge", "Success", "Executing dedicated Edge close")
        return ProcessManager.kill_process_by_name("msedge.exe")

    @staticmethod
    def open_vscode() -> bool:
        """Explicit handler to launch Visual Studio Code."""
        logger.log_command("open_vscode", "Success", "Executing dedicated VS Code launch")
        return AppController.open_app("code")

    @staticmethod
    def close_vscode() -> bool:
        """Explicit handler to terminate VS Code."""
        from controllers.process_manager import ProcessManager
        logger.log_command("close_vscode", "Success", "Executing dedicated VS Code close")
        return ProcessManager.kill_process_by_name("Code.exe")

    @staticmethod
    def open_spotify() -> bool:
        """Explicit handler to launch Spotify."""
        logger.log_command("open_spotify", "Success", "Executing dedicated Spotify launch")
        return AppController.open_app("start spotify")

    @staticmethod
    def close_spotify() -> bool:
        """Explicit handler to terminate Spotify."""
        from controllers.process_manager import ProcessManager
        logger.log_command("close_spotify", "Success", "Executing dedicated Spotify close")
        return ProcessManager.kill_process_by_name("Spotify.exe")

    @staticmethod
    def open_discord() -> bool:
        """Explicit handler to launch Discord."""
        logger.log_command("open_discord", "Success", "Executing dedicated Discord launch")
        return AppController.open_app("discord")

    @staticmethod
    def close_discord() -> bool:
        """Explicit handler to terminate Discord."""
        from controllers.process_manager import ProcessManager
        logger.log_command("close_discord", "Success", "Executing dedicated Discord close")
        return ProcessManager.kill_process_by_name("Discord.exe")

