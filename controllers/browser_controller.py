import time
import webbrowser
import subprocess
from utils.logger import logger
from controllers.window_controller import WindowController

class BrowserController:
    # Predefined popular sites mapping
    SITES_MAPPING = {
        "youtube": "https://www.youtube.com",
        "github": "https://github.com",
        "google": "https://www.google.com",
        "stackoverflow": "https://stackoverflow.com",
        "leetcode": "https://leetcode.com",
        "gmail": "https://mail.google.com",
        "chatgpt": "https://chat.openai.com",
        "gemini": "https://gemini.google.com"
    }

    @staticmethod
    def open_website(target: str) -> bool:
        """Opens a website in the default browser."""
        target_lower = target.lower().strip()
        url = BrowserController.SITES_MAPPING.get(target_lower)
        
        if not url:
            # If target has dot or common endings, treat as direct URL
            if "." in target_lower or any(suffix in target_lower for suffix in [".com", ".org", ".net", ".in", ".edu"]):
                url = target_lower if target_lower.startswith("http") else f"https://{target_lower}"
            else:
                # Default to Google Search
                url = f"https://www.google.com/search?q={target_lower}"

        try:
            logger.log_info(f"Opening website: {url}")
            webbrowser.open(url)
            return True
        except Exception as e:
            logger.log_error(f"Failed to open website {url}: {e}")
            return False

    @staticmethod
    def close_website(target: str) -> bool:
        """
        Closes the active tab if it matches target website.
        Sends Ctrl + W to request active tab close.
        """
        target_lower = target.lower().strip()
        
        # Get active window info to verify match
        hwnd, title, pid = WindowController.get_active_window_info()
        
        # Check if target domain is in window title (e.g. "YouTube" in window title)
        if hwnd and target_lower in title.lower():
            logger.log_info(f"Closing active browser tab for '{target}' (Title: '{title}').")
            WindowController.safe_hotkey("ctrl", "w")
            return True
            
        logger.log_error(f"Cannot close '{target}': it is not the active browser tab (Active: '{title}').")
        return False

    @staticmethod
    def open_new_tab() -> bool:
        """Opens a new browser tab."""
        WindowController.safe_hotkey("ctrl", "t")
        return True

    @staticmethod
    def refresh_tab() -> bool:
        """Refreshes the current active browser tab."""
        WindowController.safe_hotkey("f5")
        return True

    @staticmethod
    def go_back() -> bool:
        """Navigates back in browser history."""
        WindowController.safe_hotkey("alt", "left")
        return True

    @staticmethod
    def go_forward() -> bool:
        """Navigates forward in browser history."""
        WindowController.safe_hotkey("alt", "right")
        return True

    @staticmethod
    def switch_tabs() -> bool:
        """Switches to the next browser tab."""
        WindowController.safe_hotkey("ctrl", "tab")
        return True

    @staticmethod
    def open_downloads() -> bool:
        """Opens browser downloads page."""
        WindowController.safe_hotkey("ctrl", "j")
        return True

    @staticmethod
    def open_history() -> bool:
        """Opens browser history page."""
        WindowController.safe_hotkey("ctrl", "h")
        return True
