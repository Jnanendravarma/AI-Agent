import os
import datetime
import ctypes
from utils.logger import logger
from ai.gemini_client import GeminiClient

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
    def copy_to_clipboard(text: str) -> bool:
        """Copies text to the Windows system clipboard using native ctypes."""
        try:
            if not ctypes.windll.user32.OpenClipboard(None):
                return False
            ctypes.windll.user32.EmptyClipboard()
            # Allocate global memory block for unicode text (utf-16le)
            h_global_mem = ctypes.windll.kernel32.GlobalAlloc(0x0040, len(text.encode('utf-16le')) + 2) # GMEM_ZEROINIT = 0x0040
            lp_str = ctypes.windll.kernel32.GlobalLock(h_global_mem)
            ctypes.cdll.msvcrt.memcpy(lp_str, text.encode('utf-16le'), len(text.encode('utf-16le')) + 2)
            ctypes.windll.kernel32.GlobalUnlock(h_global_mem)
            # Set Clipboard Data (CF_UNICODETEXT = 13)
            ctypes.windll.user32.SetClipboardData(13, h_global_mem)
            ctypes.windll.user32.CloseClipboard()
            return True
        except Exception as e:
            logger.log_error(f"Failed to copy text to Windows clipboard: {e}")
            return False

    @staticmethod
    def take_screenshot() -> tuple[bool, str]:
        """
        Captures a screenshot of the system's screen,
        saves it in the 'screenshots' directory,
        and returns the success status and saved path.
        """
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        screenshot_dir = os.path.join(base_dir, "screenshots")
        
        try:
            os.makedirs(screenshot_dir, exist_ok=True)
        except Exception as e:
            logger.log_error(f"Failed to create screenshots folder: {e}")
            return False, "Failed to create screenshot folder."

        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"{timestamp}.png"
        filepath = os.path.join(screenshot_dir, filename)

        try:
            if PYAUTOGUI_AVAILABLE:
                screenshot = pyautogui.screenshot()
                screenshot.save(filepath)
                logger.log_command("Screenshot System", "Success", f"Screenshot saved: {filepath}")
                return True, filepath
            elif PIL_AVAILABLE:
                screenshot = ImageGrab.grab()
                screenshot.save(filepath)
                logger.log_command("Screenshot System", "Success", f"Screenshot saved: {filepath}")
                return True, filepath
            else:
                return False, "Neither PyAutoGUI nor Pillow libraries are available."
        except Exception as e:
            logger.log_error(f"Failed to capture screenshot: {e}")
            return False, f"Failed to save screenshot: {str(e)}"

    @classmethod
    def analyze_screenshot(cls, gemini_client: GeminiClient, query: str) -> tuple[bool, str]:
        """Takes a screenshot and queries Gemini Vision to explain it or analyze errors."""
        success, filepath = cls.take_screenshot()
        if not success:
            return False, "Failed to capture screenshot for vision analysis."

        try:
            from PIL import Image
            img = Image.open(filepath)
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

    @classmethod
    def ocr_screenshot(cls, gemini_client: GeminiClient) -> tuple[bool, str]:
        """Captures a screenshot, extracts all text using Gemini Vision, and copies it to clipboard."""
        success, filepath = cls.take_screenshot()
        if not success:
            return False, "Failed to capture screenshot for OCR extraction."

        try:
            from PIL import Image
            img = Image.open(filepath)
        except Exception as e:
            logger.log_error(f"Failed to load image for OCR: {e}")
            return False, f"Failed to load screenshot image file: {e}"

        prompt = """
Extract all visible text from this image exactly as it appears. 
Do not include any explanation or extra text, just output the extracted text.
If no text is found, output nothing.
"""
        response_text, err = gemini_client.generate_content(prompt, image=img, model_name="gemini-2.5-flash")
        if err:
            return False, f"Gemini OCR extraction failed: {err}"
            
        text = response_text.strip()
        if not text:
            return True, "No text was detected on the screen."
            
        # Copy to clipboard
        copied = cls.copy_to_clipboard(text)
        copied_msg = " and copied it to your clipboard" if copied else " (failed to copy to clipboard)"
        
        # Truncate output for speaking
        short_text = text[:150] + "..." if len(text) > 150 else text
        return True, f"I have extracted the following text{copied_msg}:\n\n{short_text}"
