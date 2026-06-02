import os
import datetime
from utils.logger import logger

# Try importing pyautogui or PIL ImageGrab as fallback
PYAUTOGUI_AVAILABLE = False
try:
    import pyautogui
    PYAUTOGUI_AVAILABLE = True
except ImportError:
    pass

PIL_AVAILABLE = False
try:
    from PIL import ImageGrab
    PIL_AVAILABLE = True
except ImportError:
    pass

class ScreenshotService:
    @staticmethod
    def take_screenshot() -> tuple[bool, str]:
        """
        Captures a screenshot of the system's screen,
        saves it in the 'screenshots' directory with a timestamped filename,
        and returns the success status and speakable response.
        """
        # Define directory path relative to workspace root
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        screenshot_dir = os.path.join(base_dir, "screenshots")
        
        # Ensure the directory exists
        try:
            os.makedirs(screenshot_dir, exist_ok=True)
        except Exception as e:
            logger.log_error(f"Failed to create screenshots folder: {e}")
            return False, "Failed to create screenshot folder."

        # Create timestamped filename: YYYY-MM-DD_HH-MM-SS.png
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"{timestamp}.png"
        filepath = os.path.join(screenshot_dir, filename)

        try:
            if PYAUTOGUI_AVAILABLE:
                # Capture using PyAutoGUI
                screenshot = pyautogui.screenshot()
                screenshot.save(filepath)
                logger.log_command("Screenshot System", "Success", f"Screenshot saved: {filepath}")
                return True, f"Screenshot captured successfully and saved as {filename}"
                
            elif PIL_AVAILABLE:
                # Capture using Pillow ImageGrab (reliable on Windows)
                screenshot = ImageGrab.grab()
                screenshot.save(filepath)
                logger.log_command("Screenshot System", "Success", f"Screenshot saved: {filepath}")
                return True, f"Screenshot captured successfully and saved as {filename}"
                
            else:
                return False, "Unable to take screenshot. Neither PyAutoGUI nor Pillow libraries are available."

        except Exception as e:
            logger.log_error(f"Failed to save screenshot: {e}")
            return False, f"Failed to save screenshot: {str(e)}"
