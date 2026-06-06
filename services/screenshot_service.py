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

    @classmethod
    def analyze_screenshot(cls, gemini_client: GeminiClient, query: str) -> tuple[bool, str]:
        """
        Takes a new screenshot and queries Gemini Vision to explain it or analyze visible errors.
        """
        # Take screen grab
        success, response = cls.take_screenshot()
        if not success:
            return False, "Failed to capture screenshot for vision analysis."

        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        screenshot_dir = os.path.join(base_dir, "screenshots")

        # Locate the latest image file inside screenshots
        try:
            if not os.path.exists(screenshot_dir):
                return False, "Screenshots folder does not exist."
            
            files = [os.path.join(screenshot_dir, f) for f in os.listdir(screenshot_dir) if f.lower().endswith(".png")]
            if not files:
                return False, "Could not find the captured screenshot file."
                
            latest_screenshot = max(files, key=os.path.getmtime)
        except Exception as e:
            logger.log_error(f"Failed to locate latest screenshot file: {e}")
            return False, "Failed to locate screenshot image on disk."

        # Load image with PIL
        try:
            from PIL import Image
            img = Image.open(latest_screenshot)
        except Exception as e:
            logger.log_error(f"Failed to load image for Gemini: {e}")
            return False, f"Failed to load screenshot image file: {e}"

        prompt = f"""
You are a desktop automation agent with vision capabilities.
The user has captured a screenshot of their desktop screen and requested:
"{query}"

Analyze the screenshot carefully and respond to their request.
If they are reporting an error, identify the window/application hosting the error and describe what is visible.
Provide a clear, brief, and actionable explanation.
"""
        response_text, err = gemini_client.generate_content(prompt, image=img, model_name="gemini-2.5-flash")
        if err:
            return False, f"Gemini Vision analysis failed: {err}"
            
        return True, response_text

