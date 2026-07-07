import os
import json
import datetime
import webbrowser
import re
import time
import socket
import importlib.util
from utils.logger import logger
from controllers.app_controller import AppController
from controllers.window_controller import WindowController
from controllers.process_manager import ProcessManager
from controllers.browser_controller import BrowserController

# AI Imports
from ai.gemini_client import GeminiClient
from ai.memory_manager import MemoryManager
from ai.context_manager import ContextManager
from ai.intent_classifier import IntentClassifier
from ai.planner import TaskPlanner
from ai.workflow_generator import WorkflowGenerator
from services.pdf_service import PDFService
from utils.preferences_manager import preferences_manager

class CommandExecutor:
    def __init__(self, config_path=None):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.base_dir = base_dir
        if config_path is None:
            config_path = os.path.join(base_dir, "config", "commands.json")
            
        self.config_path = config_path
        self.commands = {}
        self.commands_lookup = {}
        self.folders = {}
        self.discovered_apps = {}
        self.custom_commands = {}
        
        # State tracking
        self.in_chat_mode = False
        self.online = self.check_internet()
        self.pending_dangerous_command = None

        # Load configurations
        self.load_commands()
        self.load_folders()
        self.discover_applications()
        self.load_custom_commands()

        # Initialize AI Modules
        self.gemini_client = GeminiClient()
        self.memory_manager = MemoryManager()
        self.context_manager = ContextManager(self.gemini_client, self.memory_manager)
        self.intent_classifier = IntentClassifier(self.gemini_client)
        self.task_planner = TaskPlanner(self.gemini_client)
        self.workflow_generator = WorkflowGenerator(self.gemini_client)

        # Dynamic Plugin Registry
        self.plugins = []
        self.load_plugins()

    def check_internet(self) -> bool:
        """Fast offline network availability check."""
        try:
            socket.setdefaulttimeout(0.8)
            socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect(("8.8.8.8", 53))
            return True
        except Exception:
            return False

    def load_commands(self):
        """Loads command mappings from commands.json."""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, "r", encoding="utf-8") as f:
                    raw_commands = json.load(f)
                
                unsorted_lookup = {}
                for cmd_key, cmd_config in raw_commands.items():
                    cmd_config["primary_key"] = cmd_key
                    primary_clean = cmd_key.lower().strip()
                    unsorted_lookup[primary_clean] = cmd_config
                    
                    aliases = cmd_config.get("aliases", [])
                    for alias in aliases:
                        alias_clean = alias.lower().strip()
                        unsorted_lookup[alias_clean] = cmd_config
                
                self.commands_lookup = {k: unsorted_lookup[k] for k in sorted(unsorted_lookup.keys(), key=len, reverse=True)}
                self.commands = raw_commands
            else:
                logger.log_error(f"Configuration file not found at {self.config_path}")
        except Exception as e:
            logger.log_error(f"Failed to load commands config: {e}")

    def load_folders(self):
        folders_path = os.path.join(self.base_dir, "config", "folders.json")
        if os.path.exists(folders_path):
            try:
                with open(folders_path, "r", encoding="utf-8") as f:
                    self.folders = json.load(f)
            except Exception as e:
                logger.log_error(f"Failed to load folders: {e}")

    def discover_applications(self):
        start_menu_user = os.path.expandvars(r'%APPDATA%\Microsoft\Windows\Start Menu\Programs')
        start_menu_system = os.path.expandvars(r'%ProgramData%\Microsoft\Windows\Start Menu\Programs')
        discovered = {}
        
        def get_shortcut_target(lnk_path):
            try:
                import winshell
                return winshell.shortcut(lnk_path).path
            except Exception:
                try:
                    import win32com.client
                    shell = win32com.client.Dispatch("WScript.Shell")
                    return shell.CreateShortCut(lnk_path).Targetpath
                except Exception:
                    return None

        for base_path in [start_menu_user, start_menu_system]:
            if not os.path.exists(base_path):
                continue
            for root, _, files in os.walk(base_path):
                for filename in files:
                    if filename.endswith(".lnk"):
                        name = os.path.splitext(filename)[0].lower().strip()
                        filepath = os.path.join(root, filename)
                        target = get_shortcut_target(filepath)
                        if target and os.path.exists(target) and target.endswith(".exe"):
                            discovered[name] = target

        self.discovered_apps = discovered

    def load_custom_commands(self):
        """Loads custom macro commands from user config."""
        custom_path = os.path.join(self.base_dir, "config", "custom_commands.json")
        if not os.path.exists(custom_path):
            try:
                os.makedirs(os.path.dirname(custom_path), exist_ok=True)
                default_custom = {
                    "start coding": ["open vs code", "open chrome", "open github website", "open command prompt"]
                }
                with open(custom_path, "w", encoding="utf-8") as f:
                    json.dump(default_custom, f, indent=2)
                self.custom_commands = default_custom
            except Exception as e:
                logger.log_error(f"Failed to create default custom commands: {e}")
        else:
            try:
                with open(custom_path, "r", encoding="utf-8") as f:
                    self.custom_commands = json.load(f)
            except Exception as e:
                logger.log_error(f"Failed to load custom commands: {e}")

    def load_plugins(self):
        """Dynamically scans and imports plugins from plugins/ directory."""
        plugins_dir = os.path.join(self.base_dir, "plugins")
        if not os.path.exists(plugins_dir):
            os.makedirs(plugins_dir, exist_ok=True)
            return

        from plugins.base_plugin import BasePlugin
        for filename in os.listdir(plugins_dir):
            if filename.endswith(".py") and filename != "base_plugin.py":
                module_name = filename[:-3]
                file_path = os.path.join(plugins_dir, filename)
                try:
                    spec = importlib.util.spec_from_file_location(module_name, file_path)
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    
                    for attr_name in dir(module):
                        attr = getattr(module, attr_name)
                        if isinstance(attr, type) and issubclass(attr, BasePlugin) and attr is not BasePlugin:
                            plugin_instance = attr(self)
                            self.plugins.append(plugin_instance)
                            logger.log_info(f"Dynamically loaded plugin: {module_name}")
                except Exception as e:
                    logger.log_error(f"Failed to dynamically load plugin {module_name}: {e}")

    def fuzzy_match_value(self, query: str, choices: list[str], threshold: int = 70) -> tuple[str, int]:
        if not query or not choices:
            return None, 0
        try:
            from rapidfuzz import process, fuzz
            match = process.extractOne(query, choices, scorer=fuzz.WRatio)
            if match and match[1] >= threshold:
                return match[0], int(match[1])
        except Exception:
            import difflib
            matches = difflib.get_close_matches(query, choices, n=1, cutoff=threshold/100.0)
            if matches:
                return matches[0], threshold
        return None, 0

    def log_history(self, command: str, result: str):
        history_path = os.path.join(self.base_dir, "history", "command_history.json")
        try:
            os.makedirs(os.path.dirname(history_path), exist_ok=True)
            history = []
            if os.path.exists(history_path):
                with open(history_path, "r", encoding="utf-8") as f:
                    history = json.load(f)
            
            history.append({
                "command": command,
                "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "result": result
            })
            history = history[-100:]
            with open(history_path, "w", encoding="utf-8") as f:
                json.dump(history, f, indent=2)
        except Exception as e:
            logger.log_error(f"Failed to save command history: {e}")

    def execute(self, spoken_text: str) -> tuple[bool, str]:
        if not spoken_text:
            return False, ""

        start_time = time.time()
        self.online = self.check_internet()
        
        cmd_clean = spoken_text.lower().strip()
        for char in "?.,!":
            cmd_clean = cmd_clean.replace(char, "")
        cmd_clean = cmd_clean.strip()

        # 1. EMERGENCY COMMANDS (Highest Priority in Router)
        emergency_triggers = ["exit assistant", "stop assistant", "terminate assistant", "shutdown assistant", "cancel", "stop", "enough", "silence", "stop talking"]
        if cmd_clean in emergency_triggers:
            from utils.response_manager import response_manager
            response_manager.stop_speaking()
            
            elapsed = time.time() - start_time
            self._print_execution_log(spoken_text, "EMERGENCY", "assistant", "Core Engine", "False", "Success", elapsed)
            
            if cmd_clean in ["exit assistant", "stop assistant", "terminate assistant", "shutdown assistant"]:
                return True, "Goodbye!"
            return True, "Stopped."

        # 2. DANGEROUS CONFIRMATION LOOP
        if self.pending_dangerous_command:
            if cmd_clean in ["yes", "yeah", "y", "sure", "do it"]:
                dangerous_cmd = self.pending_dangerous_command
                self.pending_dangerous_command = None
                success, response = self.execute_dangerous_command(dangerous_cmd)
            elif cmd_clean in ["no", "cancel", "dont", "do not"]:
                self.pending_dangerous_command = None
                success, response = True, "Operation cancelled."
            else:
                success, response = False, "Are you sure? Please answer yes or no."
            
            elapsed = time.time() - start_time
            self._print_execution_log(spoken_text, "CONFIRMATION", "dangerous_action", "Core Engine", "False", "Success" if success else "Failed", elapsed)
            return success, response

        dangerous_patterns = ["shutdown pc", "restart computer", "delete file", "empty recycle bin", "reset settings"]
        if any(p in cmd_clean for p in dangerous_patterns):
            self.pending_dangerous_command = spoken_text
            elapsed = time.time() - start_time
            self._print_execution_log(spoken_text, "DANGEROUS_TRIGGER", "system", "Core Engine", "False", "Success", elapsed)
            return True, "Are you sure?"

        # 3. LOCAL INTENT CLASSIFICATION (Issue 9)
        classification = self.intent_classifier.classify_locally(
            spoken_text,
            discovered_apps=list(self.discovered_apps.keys()),
            commands_lookup=list(self.commands_lookup.keys())
        )
        intent = classification.get("intent", "CHAT")
        entities = classification.get("entities", {})
        target = entities.get("target", "")

        # Execution State
        success = False
        response = ""
        executed_module = "Core Engine"
        gemini_used = "False"

        # 4. PRIORITY-BASED ROUTING
        # A. Window Commands (Priority 2)
        if intent == "WINDOW_CONTROL":
            action = entities.get("action", "")
            success = WindowController.execute_action(action, target)
            response = f"Executing window action: {action}" if success else f"Failed to perform window action: {action}"
            executed_module = "Window Controller"

        # B. Application Commands (Priority 3)
        elif intent == "CLOSE_APPLICATION":
            # App termination
            app_path = self.discovered_apps.get(target)
            exec_name = os.path.basename(app_path) if app_path else f"{target}.exe"
            success = ProcessManager.kill_process_by_name(exec_name)
            response = f"Closing {target.title()}" if success else f"Process {exec_name} is not running."
            executed_module = "App Controller (Close)"

        elif intent == "OPEN_APPLICATION":
            # App launching
            app_path = self.discovered_apps.get(target) or target
            success = AppController.open_app(app_path)
            response = f"Opening {target.title()}" if success else f"Failed to open application: {target}."
            executed_module = "App Controller (Open)"

        # C. Website Commands (Priority 4)
        elif intent == "CLOSE_WEBSITE":
            # Close active website tab
            success = BrowserController.close_website(target)
            response = f"Closing active tab for {target.title()}" if success else f"YouTube/Browser tab was not active or could not be closed."
            executed_module = "Browser Controller (Close)"

        elif intent == "OPEN_WEBSITE":
            # Launch website URL
            success = BrowserController.open_website(target)
            response = f"Opening {target.title()} website." if success else f"Failed to launch website: {target}."
            executed_module = "Browser Controller (Open)"

        # D. System / Search Commands (Priority 5)
        elif intent == "SYSTEM_CONTROL":
            if any(w in cmd_clean for w in ["volume", "mute", "unmute", "sound"]):
                from services.volume_service import VolumeService
                success, response = VolumeService.execute_volume_command(spoken_text)
                executed_module = "System Controller (Volume)"
            elif "brightness" in cmd_clean:
                from services.brightness_service import BrightnessService
                success, response = BrightnessService.execute_brightness_command(spoken_text)
                executed_module = "System Controller (Brightness)"
            else:
                from services.system_info_service import SystemInfoService
                success, response = SystemInfoService.execute_system_info_command(spoken_text)
                executed_module = "System Controller (Diagnostics)"

        elif intent == "SEARCH":
            query = entities.get("query", spoken_text)
            from services.search_service import SearchService
            success, response = SearchService.execute_search(spoken_text)
            executed_module = "Search Controller"

        # E. AI Chat / Task Planning Commands (Priority 6 - Gemini Route)
        elif intent == "CHAT" or intent == "TASK_PLANNER":
            chat_command = entities.get("chat_command")
            if chat_command == "start":
                self.in_chat_mode = True
                response = "Chat mode is now active. You can ask me to write code, explain logic, or teach you concepts. What would you like to discuss?"
                success = True
                executed_module = "Core Engine"
            elif chat_command == "stop":
                self.in_chat_mode = False
                response = "Exiting chat mode. Returning to standard assistant."
                success = True
                executed_module = "Core Engine"
            else:
                if self.in_chat_mode:
                    if not self.online:
                        success = False
                        response = "Internet connection is currently unavailable. General AI Chat is offline."
                        executed_module = "AI Engine"
                    else:
                        gemini_used = "True"
                        success, response = self._handle_chat_mode(spoken_text)
                        executed_module = "AI Engine"
                else:
                    # Automation command fuzzy correction suggestions fallback if not in chat mode
                    all_suggestions = list(self.commands_lookup.keys())
                    for f_name in self.folders.keys():
                        all_suggestions.append(f"open {f_name}")
                    for app_name in self.discovered_apps.keys():
                        all_suggestions.append(f"open {app_name}")
                    best_suggestion, sugg_score = self.fuzzy_match_value(cmd_clean, all_suggestions, threshold=70)
                    
                    success = False
                    if best_suggestion:
                        response = f"Command not recognized. Did you mean '{best_suggestion}'?"
                    else:
                        response = "AI Chat mode is currently inactive. Say 'Start Chat Mode' to ask educational or AI queries."
                    executed_module = "Core Engine"

        # Apply basic translation rules
        if response:
            pref_lang = preferences_manager.get("language", "en")
            if pref_lang == "te":
                response = self._translate_telugu_locally(response)
            elif pref_lang == "hi":
                response = self._translate_hindi_locally(response)

        # Log output exactly as requested (Issue 10)
        elapsed = time.time() - start_time
        self._print_execution_log(spoken_text, intent, target, executed_module, gemini_used, "Success" if success else "Failed", elapsed)
        
        self.log_history(spoken_text, "Success" if success else "Failed")
        logger.log_interaction(spoken_text, intent, "Success" if success else "Failed", gemini_used, elapsed, None if success else response)

        return success, response

    def _print_execution_log(self, speech, intent, target, executed_module, gemini_used, result, elapsed):
        """Prints log format matching requirements."""
        print(f"\nRecognized: {speech}")
        print(f"Intent: {intent}")
        print(f"Target: {target if target else 'None'}")
        print(f"Executed: {executed_module}")
        print(f"Gemini Used: {gemini_used}")
        print(f"Result: {result}")
        print(f"Execution Time: {elapsed:.2f} seconds\n")

    def execute_dangerous_command(self, command: str) -> tuple[bool, str]:
        cmd_clean = command.lower().strip()
        import subprocess
        
        if "shutdown pc" in cmd_clean:
            subprocess.Popen("shutdown /s /t 0", shell=True)
            return True, "Shutting down the computer."
            
        elif "restart computer" in cmd_clean:
            subprocess.Popen("shutdown /r /t 0", shell=True)
            return True, "Restarting the computer."
            
        elif "delete file" in cmd_clean:
            parts = command.split("delete file")
            if len(parts) > 1:
                filename = parts[1].strip()
                if os.path.exists(filename):
                    try:
                        os.remove(filename)
                        return True, f"Deleted file '{filename}'."
                    except Exception as e:
                        return False, f"Failed to delete file: {e}"
            return False, "File not found or not specified."
            
        elif "empty recycle bin" in cmd_clean:
            try:
                import ctypes
                ctypes.windll.shell32.SHEmptyRecycleBinW(None, None, 7)
                return True, "Recycle Bin emptied successfully."
            except Exception as e:
                logger.log_error(f"Empty recycle bin failed: {e}")
                return False, f"Failed to empty Recycle Bin: {e}"
                
        elif "reset settings" in cmd_clean:
            preferences_manager.preferences = {
                "language": "en",
                "username": "Jnanendra",
                "speech_rate": 1.0,
                "volume": 1.0,
                "theme": "dark",
                "favorite_browser": "chrome",
                "preferred_ide": "vscode",
                "favorite_player": "spotify",
                "coding_folder": "",
                "learned_assets": {}
            }
            preferences_manager.save_preferences()
            preferences_manager._sync_voice_config()
            return True, "All user settings and preferences reset to defaults."
            
        return False, "Unknown dangerous command."

    def _translate_telugu_locally(self, text: str) -> str:
        text_lower = text.lower()
        if "opening" in text_lower:
            target = text.replace("Opening", "").replace("discovered application", "").strip()
            return f"{target} open chesthunna."
        if "closing" in text_lower:
            target = text.replace("Closing", "").strip()
            return f"{target} close chesthunna."
        return text

    def _translate_hindi_locally(self, text: str) -> str:
        text_lower = text.lower()
        if "opening" in text_lower:
            target = text.replace("Opening", "").replace("discovered application", "").strip()
            return f"{target} khol raha hoon."
        if "closing" in text_lower:
            target = text.replace("Closing", "").strip()
            return f"{target} band kar raha hoon."
        return text

    def _handle_chat_mode(self, command: str) -> tuple[bool, str]:
        history = self.memory_manager.get_recent_history(limit=10)
        history_str = ""
        for item in history:
            role_lbl = "User" if item["role"] == "user" else "Assistant"
            history_str += f"{role_lbl}: {item['message']}\n"

        system_prompt = """You are an intelligent desktop AI assistant.
Always respond in the same language used by the user.
If the user speaks Telugu (or Telglish), respond in Telugu/Telglish.
If the user speaks English, respond in English.
If the user speaks Hindi (or Hinglish), respond in Hindi/Hinglish.
Keep responses concise and informative.
You support programming help, debugging, project guidance, code generation, and concept explanations.
"""
        prompt = f"{system_prompt}\nRecent Chat History:\n{history_str}\nUser: {command}\nAssistant:"
        response, err = self.gemini_client.generate_content(prompt)
        if err:
            return False, err
        return True, response

    def _load_workflow_names(self) -> list[str]:
        workflows_path = os.path.join(self.base_dir, "workflows", "workflows.json")
        if os.path.exists(workflows_path):
            try:
                with open(workflows_path, "r", encoding="utf-8") as f:
                    w = json.load(f)
                    return list(w.keys())
            except Exception:
                pass
        return []
