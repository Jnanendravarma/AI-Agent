import time
from utils.logger import logger

# Try importing dependencies
PYAUTOGUI_AVAILABLE = False
try:
    import pyautogui
    PYAUTOGUI_AVAILABLE = True
    pyautogui.FAILSAFE = True
except ImportError:
    logger.log_error("pyautogui library not installed. PyAutoGUI fallbacks will be disabled.")

PYWIN32_AVAILABLE = False
try:
    import win32gui
    import win32con
    PYWIN32_AVAILABLE = True
except ImportError:
    logger.log_error("pywin32 (win32gui/win32con) library not installed. Enterprise window actions disabled.")

class WindowController:
    @staticmethod
    def safe_hotkey(*args):
        """
        Sends hotkey combination using PyAutoGUI and immediately releases standard
        modifier keys to prevent keys from getting 'stuck' in the OS.
        """
        if not PYAUTOGUI_AVAILABLE:
            return
        try:
            pyautogui.hotkey(*args)
        finally:
            # Release all standard modifiers to prevent sticking
            for key in ["win", "ctrl", "alt", "shift"]:
                try:
                    pyautogui.keyUp(key)
                except Exception:
                    pass

    @staticmethod
    def execute_action(action: str) -> bool:
        """
        Executes window automation actions.
        Uses win32gui/win32con for direct enterprise-grade OS-level actions,
        and falls back to safe PyAutoGUI hotkeys if necessary.
        """
        action = action.lower()
        hwnd = None

        if PYWIN32_AVAILABLE:
            try:
                hwnd = win32gui.GetForegroundWindow()
            except Exception as e:
                logger.log_error(f"Error fetching active window handle via win32gui: {e}")

        try:
            if action == "minimize":
                if hwnd and hwnd != 0:
                    win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
                    return True
                elif PYAUTOGUI_AVAILABLE:
                    WindowController.safe_hotkey("win", "down")
                    time.sleep(0.2)
                    WindowController.safe_hotkey("win", "down")
                    return True
                return False
                
            elif action == "maximize":
                if hwnd and hwnd != 0:
                    win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
                    return True
                elif PYAUTOGUI_AVAILABLE:
                    WindowController.safe_hotkey("win", "up")
                    return True
                return False
                
            elif action == "restore":
                if hwnd and hwnd != 0:
                    win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                    return True
                elif PYAUTOGUI_AVAILABLE:
                    WindowController.safe_hotkey("win", "down")
                    return True
                return False
                
            elif action == "close_current":
                if hwnd and hwnd != 0:
                    # Post message is standard graceful way to request window close
                    win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
                    return True
                elif PYAUTOGUI_AVAILABLE:
                    WindowController.safe_hotkey("alt", "f4")
                    return True
                return False
                
            elif action == "switch_tab":
                if PYAUTOGUI_AVAILABLE:
                    WindowController.safe_hotkey("ctrl", "tab")
                    return True
                return False
                
            elif action == "show_desktop":
                if PYAUTOGUI_AVAILABLE:
                    WindowController.safe_hotkey("win", "d")
                    return True
                return False
                
            elif action == "open_task_manager":
                # Launch taskmgr directly rather than relying on hotkeys which can be blocked
                import subprocess
                subprocess.Popen("taskmgr", shell=True)
                return True
                
            else:
                logger.log_error(f"Unknown window action requested: {action}")
                return False
                
        except Exception as e:
            logger.log_error(f"Window controller failed during action '{action}': {e}")
            return False
