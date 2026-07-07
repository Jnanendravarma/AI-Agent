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
    import win32process
    PYWIN32_AVAILABLE = True
except ImportError:
    logger.log_error("pywin32 library not installed. Direct OS window actions disabled.")

class WindowController:
    @staticmethod
    def get_active_window_info() -> tuple[any, str, int]:
        """
        Retrieves the handle, title, and process ID of the currently active window.
        Returns (hwnd, title, pid).
        """
        if not PYWIN32_AVAILABLE:
            return None, "", 0
        try:
            hwnd = win32gui.GetForegroundWindow()
            if hwnd and hwnd != 0:
                title = win32gui.GetWindowText(hwnd)
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                return hwnd, title, pid
        except Exception as e:
            logger.log_error(f"Error fetching active window info: {e}")
        return None, "", 0

    @staticmethod
    def find_window_by_title(target_title: str) -> any:
        """Finds the first window handle whose title contains target_title."""
        if not PYWIN32_AVAILABLE:
            return None
        matching_hwnds = []
        
        def enum_windows_callback(hwnd, extra):
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd)
                if target_title.lower() in title.lower():
                    matching_hwnds.append(hwnd)
                    
        try:
            win32gui.EnumWindows(enum_windows_callback, None)
        except Exception as e:
            logger.log_error(f"Error enumerating windows: {e}")
            
        return matching_hwnds[0] if matching_hwnds else None

    @staticmethod
    def safe_hotkey(*args):
        """Sends hotkeys securely and releases modifier keys to avoid stuck states."""
        if not PYAUTOGUI_AVAILABLE:
            return
        try:
            pyautogui.hotkey(*args)
        finally:
            for key in ["win", "ctrl", "alt", "shift"]:
                try:
                    pyautogui.keyUp(key)
                except Exception:
                    pass

    @staticmethod
    def execute_action(action: str, target: str = None) -> bool:
        """
        Executes active window management operations.
        Retrieves active window metrics (HWND, title, PID) first before dispatching actions.
        """
        action = action.lower().strip()
        hwnd, title, pid = WindowController.get_active_window_info()

        logger.log_info(f"Window Action '{action}' target='{target}' | Active Window Title: '{title}', HWND: {hwnd}, PID: {pid}")

        try:
            if action == "minimize":
                if hwnd and hwnd != 0:
                    win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
                    return True
                elif PYAUTOGUI_AVAILABLE:
                    WindowController.safe_hotkey("win", "down")
                    time.sleep(0.1)
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

            elif action == "close_active":
                if hwnd and hwnd != 0:
                    win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
                    return True
                elif PYAUTOGUI_AVAILABLE:
                    WindowController.safe_hotkey("alt", "f4")
                    return True
                return False

            elif action == "bring_to_front":
                if target:
                    target_hwnd = WindowController.find_window_by_title(target)
                    if target_hwnd:
                        try:
                            # If minimized, restore first
                            if win32gui.IsIconic(target_hwnd):
                                win32gui.ShowWindow(target_hwnd, win32con.SW_RESTORE)
                            win32gui.SetForegroundWindow(target_hwnd)
                            return True
                        except Exception as e:
                            logger.log_error(f"Failed to set foreground window: {e}")
                return False

            elif action == "switch_window":
                if PYAUTOGUI_AVAILABLE:
                    WindowController.safe_hotkey("alt", "tab")
                    return True
                return False

            elif action == "show_desktop":
                if PYAUTOGUI_AVAILABLE:
                    WindowController.safe_hotkey("win", "d")
                    return True
                return False

            elif action == "open_task_manager":
                import subprocess
                subprocess.Popen("taskmgr", shell=True)
                return True

            else:
                logger.log_error(f"Invalid window action: {action}")
                return False

        except Exception as e:
            logger.log_error(f"Window controller failed during action '{action}': {e}")
            return False
