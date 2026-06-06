import os
import json
import datetime
import webbrowser
import re
from utils.logger import logger
from controllers.app_controller import AppController
from controllers.window_controller import WindowController
from controllers.process_manager import ProcessManager

# AI Imports
from ai.gemini_client import GeminiClient
from ai.memory_manager import MemoryManager
from ai.context_manager import ContextManager
from ai.intent_classifier import IntentClassifier
from ai.planner import TaskPlanner
from ai.workflow_generator import WorkflowGenerator
from services.pdf_service import PDFService

class CommandExecutor:
    def __init__(self, config_path=None):
        if config_path is None:
            # Set default path relative to workspace root
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            config_path = os.path.join(base_dir, "config", "commands.json")
            
        self.config_path = config_path
        self.commands = {}
        self.commands_lookup = {}
        self.folders = {}
        self.discovered_apps = {}
        
        # Load commands configuration
        self.load_commands()
        # Load custom folder mappings
        self.load_folders()
        # Perform Windows Start Menu application discovery
        self.discover_applications()

        # Initialize AI Modules
        self.gemini_client = GeminiClient()
        self.memory_manager = MemoryManager()
        self.context_manager = ContextManager(self.gemini_client, self.memory_manager)
        self.intent_classifier = IntentClassifier(self.gemini_client)
        self.task_planner = TaskPlanner(self.gemini_client)
        self.workflow_generator = WorkflowGenerator(self.gemini_client)


    def load_commands(self):
        """Loads command mappings from the JSON configuration file and flat-maps aliases."""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, "r", encoding="utf-8") as f:
                    raw_commands = json.load(f)
                
                # Build a flattened lookup table mapping both primary triggers and aliases
                unsorted_lookup = {}
                for cmd_key, cmd_config in raw_commands.items():
                    # Save reference to original primary key for dynamic display names
                    cmd_config["primary_key"] = cmd_key
                    
                    # Register primary key (lowercase, stripped)
                    primary_clean = cmd_key.lower().strip()
                    unsorted_lookup[primary_clean] = cmd_config
                    
                    # Register all aliases
                    aliases = cmd_config.get("aliases", [])
                    for alias in aliases:
                        alias_clean = alias.lower().strip()
                        unsorted_lookup[alias_clean] = cmd_config
                
                # Sort lookup table by key length descending to prioritize longer phrases
                self.commands_lookup = {k: unsorted_lookup[k] for k in sorted(unsorted_lookup.keys(), key=len, reverse=True)}
                self.commands = raw_commands
                print(f"Loaded {len(self.commands)} command blocks and built {len(self.commands_lookup)} unique match patterns.")
            else:
                logger.log_error(f"Configuration file not found at {self.config_path}")
                self.commands = {}
                self.commands_lookup = {}
        except Exception as e:
            logger.log_error(f"Failed to load commands config: {e}")
            self.commands = {}
            self.commands_lookup = {}

    def load_folders(self):
        """Loads customized folder voiced mappings."""
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        folders_path = os.path.join(base_dir, "config", "folders.json")
        if os.path.exists(folders_path):
            try:
                with open(folders_path, "r", encoding="utf-8") as f:
                    self.folders = json.load(f)
            except Exception as e:
                logger.log_error(f"Failed to load folders: {e}")
                self.folders = {}
        else:
            self.folders = {}

    def discover_applications(self):
        """Scans Windows Start Menu paths for installed apps and caches them."""
        start_menu_user = os.path.expandvars(r'%APPDATA%\Microsoft\Windows\Start Menu\Programs')
        start_menu_system = os.path.expandvars(r'%ProgramData%\Microsoft\Windows\Start Menu\Programs')
        
        discovered = {}
        
        # Helper to safely retrieve shortcut targets
        def get_shortcut_target(lnk_path):
            try:
                import winshell
                shell_link = winshell.shortcut(lnk_path)
                return shell_link.path
            except Exception:
                try:
                    import win32com.client
                    shell = win32com.client.Dispatch("WScript.Shell")
                    shortcut = shell.CreateShortCut(lnk_path)
                    return shortcut.Targetpath
                except Exception:
                    return None

        # Recursively walk the start menus
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

        # Cache applications in a dedicated JSON file
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.apps_cache_path = os.path.join(base_dir, "config", "apps_cache.json")
        try:
            os.makedirs(os.path.dirname(self.apps_cache_path), exist_ok=True)
            with open(self.apps_cache_path, "w", encoding="utf-8") as f:
                json.dump(discovered, f, indent=2)
            self.discovered_apps = discovered
            print(f"Dynamically discovered {len(discovered)} installed applications and updated cache.")
        except Exception as e:
            logger.log_error(f"Failed to cache discovered apps: {e}")
            self.discovered_apps = discovered

    def fuzzy_match_value(self, query: str, choices: list[str], threshold: int = 70) -> tuple[str, int]:
        """Fuzzy string matching utility using rapidfuzz with difflib fallback."""
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
        """Persists executed commands to local history tracker."""
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        history_path = os.path.join(base_dir, "history", "command_history.json")
        try:
            os.makedirs(os.path.dirname(history_path), exist_ok=True)
            history = []
            if os.path.exists(history_path):
                with open(history_path, "r", encoding="utf-8") as f:
                    history = json.load(f)
            
            entry = {
                "command": command,
                "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "result": result
            }
            history.append(entry)
            history = history[-100:]  # Limit log size
            
            with open(history_path, "w", encoding="utf-8") as f:
                json.dump(history, f, indent=2)
        except Exception as e:
            logger.log_error(f"Failed to save command history: {e}")

    def get_history_summary(self) -> str:
        """Retrieves a summarized speakable history of recent executions."""
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        history_path = os.path.join(base_dir, "history", "command_history.json")
        if not os.path.exists(history_path):
            return "No history log available."
        try:
            with open(history_path, "r", encoding="utf-8") as f:
                history = json.load(f)
            if not history:
                return "Your command history is empty."
            recent = history[-5:]
            lines = []
            for item in recent:
                lines.append(f"'{item['command']}' resulting in {item['result']}")
            return "Your recent command history includes: " + "; and ".join(lines)
        except Exception as e:
            logger.log_error(f"Failed to read command history: {e}")
            return "Unable to retrieve command history."

    def _load_workflow_names(self) -> list[str]:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        workflows_path = os.path.join(base_dir, "workflows", "workflows.json")
        if os.path.exists(workflows_path):
            try:
                with open(workflows_path, "r", encoding="utf-8") as f:
                    w = json.load(f)
                    return list(w.keys())
            except Exception:
                pass
        return []

    def find_command(self, spoken_text: str):
        """
        Attempts to match the spoken text to registered commands.
        Uses exact matching first, then falls back to fuzzy/substring matching.
        Returns the matched trigger phrase and its configuration, or (None, None).
        """
        if not spoken_text:
            return None, None

        # Normalize and clean spoken text
        cleaned_text = spoken_text.strip().lower()
        for char in "?.,!":
            cleaned_text = cleaned_text.replace(char, "")
        cleaned_text = cleaned_text.strip()

        # 1. Exact Match Check
        if cleaned_text in self.commands_lookup:
            return cleaned_text, self.commands_lookup[cleaned_text]

        # 2. Substring Match Check
        for trigger_phrase, cmd_config in self.commands_lookup.items():
            if trigger_phrase in cleaned_text:
                return trigger_phrase, cmd_config

        # 3. Reverse Substring Check
        for trigger_phrase, cmd_config in self.commands_lookup.items():
            if cleaned_text in trigger_phrase and len(cleaned_text) >= 4:
                return trigger_phrase, cmd_config

        # 4. Global Fuzzy Matching with triggers
        best_trigger, score = self.fuzzy_match_value(cleaned_text, list(self.commands_lookup.keys()), threshold=80)
        if best_trigger:
            return best_trigger, self.commands_lookup[best_trigger]

        return None, None

    def execute(self, spoken_text: str) -> tuple[bool, str]:
        """
        Phase 3 Orchestrated Execution. Resolves context, classifies intent,
        executes task, frames multilingual output, and logs to conversational memory.
        """
        if not spoken_text:
            return False, ""

        # 1. Resolve pronouns/context
        resolved_command = self.context_manager.resolve_context(spoken_text)

        # 2. Classify intent
        classification = self.intent_classifier.classify(resolved_command)
        intent = classification.get("intent", "chat_mode")
        entities = classification.get("entities", {})

        success = False
        response = ""

        # 3. Route according to classified intent
        if intent == "chat_mode":
            success, response = self._handle_chat_mode(resolved_command)

        elif intent == "task_planning":
            success, response = self._handle_task_planning(resolved_command)

        elif intent == "document_analysis":
            success, response = PDFService.execute_pdf_action(self.gemini_client, resolved_command)

        elif intent == "screenshot_analysis":
            from services.screenshot_service import ScreenshotService
            success, response = ScreenshotService.analyze_screenshot(self.gemini_client, resolved_command)

        elif intent == "workflow_execution":
            project_name = entities.get("project_name")
            if project_name:
                success, response = self._handle_dynamic_workflow(project_name)
            else:
                from services.workflow_service import WorkflowService
                success, response = WorkflowService.execute_workflow(resolved_command)

        else:
            # Route to local device control block
            success, response = self._execute_local_command(resolved_command, intent, entities)

        # 4. Multilingual rephrasing fallback for status messages
        if response:
            response = self._ensure_same_language(spoken_text, response)

        # 5. Log interaction to conversational memory
        self.memory_manager.add_interaction(role="user", message=spoken_text)
        self.memory_manager.add_interaction(role="assistant", message=response, context={"intent": intent})

        return success, response

    def _handle_chat_mode(self, command: str) -> tuple[bool, str]:
        """Runs interactive AI chat session with full context memory."""
        if command.lower().strip() == "start chat mode":
            return True, "Chat mode is now active. You can ask me to write code, explain logic, or teach you concepts. What would you like to discuss?"

        history = self.memory_manager.get_recent_history(limit=10)
        history_str = ""
        for item in history:
            role_lbl = "User" if item["role"] == "user" else "Assistant"
            history_str += f"{role_lbl}: {item['message']}\n"

        system_prompt = """You are an intelligent desktop AI assistant.
Always respond in the same language used by the user.
If the user speaks Telugu (or Telglish/Latin Telugu), respond in Telugu/Telglish.
If the user speaks English, respond in English.
If the user speaks Hindi (or Hinglish/Latin Hindi), respond in Hindi/Hinglish.
Keep responses concise and informative.
Never change language unless requested.
You support programming help, interview prep, debugging, project guidance, code generation, and concept explanations.
"""
        prompt = f"{system_prompt}\nRecent Chat History:\n{history_str}\nUser: {command}\nAssistant:"
        response, err = self.gemini_client.generate_content(prompt, model_name="gemini-2.5-flash")
        if err:
            return False, f"Could not generate chat response: {err}"
        return True, response

    def _handle_task_planning(self, command: str) -> tuple[bool, str]:
        """Uses AI Planner to generate and execute action plan for compound tasks."""
        apps_list = list(self.discovered_apps.keys())
        folders_list = list(self.folders.keys())

        plan = self.task_planner.generate_plan(command, apps_list, folders_list)
        if not plan:
            return False, "I couldn't formulate a plan to satisfy that request."

        executed_steps = []
        for step in plan:
            stype = step.get("type")
            target = step.get("target")
            if not target:
                continue

            try:
                if stype == "open_app":
                    app_path = self.discovered_apps.get(target.lower()) or target
                    if AppController.open_app(app_path):
                        executed_steps.append(f"Opened {target.title()}")
                elif stype == "open_folder":
                    folder_path = self.folders.get(target.lower()) or target
                    expanded = os.path.expanduser(folder_path)
                    if os.path.exists(expanded):
                        os.startfile(expanded)
                        executed_steps.append(f"Opened folder {target.title()}")
                elif stype == "open_url":
                    webbrowser.open(target)
                    executed_steps.append(f"Opened URL {target}")
            except Exception as e:
                logger.log_error(f"Planning execution step failed: {e}")

        if executed_steps:
            return True, "Completed task steps: " + ", ".join(executed_steps)
        return False, "No planning tasks could be completed."

    def _handle_dynamic_workflow(self, project_name: str) -> tuple[bool, str]:
        """Uses WorkflowGenerator to analyze workspaces and launch project environments."""
        plan = self.workflow_generator.generate_dynamic_workflow(project_name, self.discovered_apps)
        if not plan:
            return False, f"Could not construct workflow for '{project_name}'."

        executed = []
        for step in plan:
            stype = step.get("type")
            target = step.get("target")
            if not target:
                continue

            try:
                if stype == "open_folder":
                    if os.path.exists(target):
                        os.startfile(target)
                        executed.append(f"opened project directory")
                elif stype == "open_app":
                    if "code" in target.lower() or "visual studio code" in target.lower():
                        project_folder = self.workflow_generator._find_project_folder(project_name)
                        if project_folder:
                            vscode_path = self.discovered_apps.get("visual studio code") or self.discovered_apps.get("vscode")
                            if vscode_path:
                                import subprocess
                                subprocess.Popen([vscode_path, project_folder], shell=True)
                                executed.append("started VS Code on project")
                                continue
                    app_path = self.discovered_apps.get(target.lower()) or target
                    if AppController.open_app(app_path):
                        executed.append(f"launched {target.title()}")
                elif stype == "open_url":
                    webbrowser.open(target)
                    executed.append(f"opened url {target}")
            except Exception as e:
                logger.log_error(f"Dynamic workflow execution step failed: {e}")

        if executed:
            return True, f"Configured workspace for {project_name.title()}: " + ", ".join(executed)
        return False, "Failed to initialize project workflow."

    def _ensure_same_language(self, query: str, response: str) -> str:
        """Adapts status messages to the language style of the user query."""
        contains_telugu = re.search(r"[\u0c00-\u0c7f]", query) or any(w in query.lower() for w in ["cheyyi", "open chey", "chastna", "pettuko"])
        contains_hindi = re.search(r"[\u0900-\u097f]", query) or any(w in query.lower() for w in ["karo", "kholo", "band kar", "rakho"])

        if not contains_telugu and not contains_hindi:
            return response

        prompt = f"""
You are a translation assistant for a desktop AI agent.
The user queried: "{query}"
The status response of the action is: "{response}"

Rephrase the status response in the EXACT same language and style (including Hinglish, Telglish, Telugu script, or Hindi script) used by the user in their query. Keep the response natural, conversational, and extremely concise.

Examples:
Query: "Chrome open cheyyi"
Status: "Opening discovered application Chrome"
Output: "Chrome open chesthunna."

Query: "Chrome band karo"
Status: "Closing Chrome"
Output: "Chrome band kar raha hoon."

Output ONLY the rephrased status response. Do not include quotes or extra commentary.
"""
        translated, err = self.gemini_client.generate_content(prompt, model_name="gemini-2.5-flash")
        if translated and not err:
            return translated.strip().strip('"')
        return response

    def _execute_local_command(self, spoken_text: str, intent: str = None, entities: dict = None) -> tuple[bool, str]:
        """
        Processes and executes the recognized command locally.
        Routes dynamically to system services, fuzzy matched configs, folder navigation,
        discovered apps, or spelling suggestion routines.
        """
        if not spoken_text:
            return False, ""

        cmd_clean = spoken_text.strip().lower()
        for char in "?.,!":
            cmd_clean = cmd_clean.replace(char, "")
        cmd_clean = cmd_clean.strip()

        # --- ROUTING BLOCK 1: Persistent Command History ---
        if cmd_clean in ["show history", "show recent commands", "recent commands", "history"]:
            response = self.get_history_summary()
            self.log_history(spoken_text, "Success")
            return True, response

        # --- ROUTING BLOCK 2: Screenshots ---
        if any(keyword in cmd_clean for keyword in ["screenshot", "capture screen", "save screenshot"]):
            from services.screenshot_service import ScreenshotService
            success, response = ScreenshotService.take_screenshot()
            self.log_history(spoken_text, "Success" if success else "Failed")
            return success, response

        # --- ROUTING BLOCK 3: Audio Control ---
        if any(keyword in cmd_clean for keyword in ["volume", "mute", "unmute", "sound"]) or intent == "volume_control":
            from services.volume_service import VolumeService
            success, response = VolumeService.execute_volume_command(spoken_text)
            self.log_history(spoken_text, "Success" if success else "Failed")
            return success, response

        # --- ROUTING BLOCK 4: Brightness Control ---
        if "brightness" in cmd_clean or intent == "brightness_control":
            from services.brightness_service import BrightnessService
            success, response = BrightnessService.execute_brightness_command(spoken_text)
            self.log_history(spoken_text, "Success" if success else "Failed")
            return success, response

        # --- ROUTING BLOCK 5: Battery and Diagnostics ---
        if any(keyword in cmd_clean for keyword in ["battery", "system information", "system info", "cpu usage", "ram usage", "memory usage", "disk usage", "disk space", "pc specs", "specs", "temperature", "temp status"]):
            from services.system_info_service import SystemInfoService
            success, response = SystemInfoService.execute_system_info_command(spoken_text)
            self.log_history(spoken_text, "Success" if success else "Failed")
            return success, response

        # --- ROUTING BLOCK 6: Local File Search & Operations ---
        if any(cmd_clean.startswith(prefix) for prefix in ["find ", "search file ", "search for file ", "open file "]) or cmd_clean in ["open it", "open file", "open last file"]:
            from services.file_search_service import FileSearchService
            if cmd_clean in ["open it", "open file", "open last file"]:
                success, response = FileSearchService.open_last_found_file()
            else:
                success, response = FileSearchService.execute_file_search(spoken_text)
            self.log_history(spoken_text, "Success" if success else "Failed")
            return success, response

        # --- ROUTING BLOCK 7: Search Automation (Google, YouTube, StackOverflow, GitHub) ---
        if any(cmd_clean.startswith(prefix) for prefix in ["search ", "google ", "find "]) or "stack overflow" in cmd_clean or "stackoverflow" in cmd_clean or "youtube" in cmd_clean or "github" in cmd_clean:
            from services.search_service import SearchService
            success, response = SearchService.execute_search(spoken_text)
            self.log_history(spoken_text, "Success" if success else "Failed")
            return success, response

        # --- ROUTING BLOCK 8: Workflow Automation ---
        if "setup" in cmd_clean or "workflow" in cmd_clean:
            from services.workflow_service import WorkflowService
            success, response = WorkflowService.execute_workflow(spoken_text)
            self.log_history(spoken_text, "Success" if success else "Failed")
            return success, response

        # --- ROUTING BLOCK 9: Folder Navigation ---
        for folder_name, folder_path in self.folders.items():
            if f"open {folder_name}" in cmd_clean or f"go to {folder_name}" in cmd_clean:
                expanded_path = os.path.expanduser(folder_path)
                if os.path.exists(expanded_path):
                    try:
                        os.startfile(expanded_path)
                        self.log_history(spoken_text, "Success")
                        return True, f"Opening folder {folder_name.title()}"
                    except Exception as e:
                        logger.log_error(f"Failed to open folder {folder_name}: {e}")
                        return False, f"Could not open the folder {folder_name}."
                else:
                    return False, f"Folder {folder_name} path does not exist."

        # --- ROUTING BLOCK 10: Dynamic Discovered Apps launching (Open) ---
        launch_verbs = ["open", "launch", "start", "run"]
        for verb in launch_verbs:
            # Allow fallback if intent classifier found app_name entity
            app_target = entities.get("app_name") if entities else None
            if cmd_clean.startswith(f"{verb} ") or (intent == "open_application" and app_target):
                if not app_target:
                    app_target = cmd_clean[len(verb) + 1:].strip()
                best_app_match, app_score = self.fuzzy_match_value(app_target, list(self.discovered_apps.keys()), threshold=75)
                if best_app_match:
                    app_path = self.discovered_apps[best_app_match]
                    success = AppController.open_app(app_path)
                    if success:
                        self.log_history(spoken_text, "Success")
                        return True, f"Opening discovered application {best_app_match.title()}"

        # --- ROUTING BLOCK 11: Dynamic Discovered Apps termination (Close) ---
        close_verbs = ["close", "terminate", "exit", "stop"]
        for verb in close_verbs:
            app_target = entities.get("app_name") if entities else None
            if cmd_clean.startswith(f"{verb} ") or (intent == "close_application" and app_target):
                if not app_target:
                    app_target = cmd_clean[len(verb) + 1:].strip()
                best_app_match, app_score = self.fuzzy_match_value(app_target, list(self.discovered_apps.keys()), threshold=75)
                if best_app_match:
                    app_path = self.discovered_apps[best_app_match]
                    exec_name = os.path.basename(app_path)
                    success = ProcessManager.kill_process_by_name(exec_name)
                    if success:
                        self.log_history(spoken_text, "Success")
                        return True, f"Closing {best_app_match.title()}"

        # --- ROUTING BLOCK 12: Configured command mappings fallback ---
        matched_phrase, cmd_config = self.find_command(spoken_text)

        if cmd_config:
            cmd_type = cmd_config.get("type")
            primary_key = cmd_config.get("primary_key", matched_phrase)
            success = False
            response = ""

            try:
                if cmd_type == "application":
                    app_cmd = cmd_config.get("command")
                    display_name = cmd_config.get("display_name", primary_key.replace("open ", "").title())
                    response = f"Opening {display_name}"
                    success = AppController.open_app(app_cmd)

                elif cmd_type == "website":
                    url = cmd_config.get("url")
                    display_name = cmd_config.get("display_name", primary_key.replace("open ", "").title())
                    response = f"Opening {display_name}"
                    webbrowser.open(url)
                    success = True

                elif cmd_type == "close":
                    proc_name = cmd_config.get("process_name")
                    display_name = cmd_config.get("display_name", primary_key.replace("close ", "").title())
                    response = f"Closing {display_name}"
                    success = ProcessManager.kill_process_by_name(proc_name)

                elif cmd_type == "window":
                    action = cmd_config.get("action")
                    response = f"Executing {primary_key.title()}"
                    success = WindowController.execute_action(action)

                elif cmd_type == "status":
                    proc_name = cmd_config.get("process_name")
                    display_name = cmd_config.get("display_name", primary_key.replace("is ", "").replace(" running", "").title())
                    is_running = AppController.is_app_running(proc_name)
                    if is_running:
                        response = f"{display_name} is currently running."
                    else:
                        response = f"{display_name} is not running."
                    success = True

                elif cmd_type == "special":
                    action = cmd_config.get("action")
                    if action == "stop":
                        response = "Stopping the assistant. Goodbye!"
                        success = True
                    else:
                        response = "Special operation executed"
                        success = True
                else:
                    response = f"Unsupported command type '{cmd_type}'"
                    logger.log_error(response)
                    success = False

            except Exception as e:
                logger.log_error(f"Error executing mapped command '{primary_key}': {e}")
                success = False
                response = f"An error occurred while executing command"

            status = "Success" if success else "Failed"
            details = None if success else f"Execution failed for action type: {cmd_type}"
            logger.log_command(spoken_text, status, details)
            self.log_history(spoken_text, status)
            return success, response

        # --- ROUTING BLOCK 13: Suggest spelling/similarity correction ---
        all_suggestions = list(self.commands_lookup.keys())
        for f_name in self.folders.keys():
            all_suggestions.append(f"open {f_name}")
        for w_name in self._load_workflow_names():
            all_suggestions.append(f"open {w_name}")
            all_suggestions.append(f"run {w_name}")
        for app_name in self.discovered_apps.keys():
            all_suggestions.append(f"open {app_name}")
            
        best_suggestion, sugg_score = self.fuzzy_match_value(cmd_clean, all_suggestions, threshold=55)
        
        self.log_history(spoken_text, "Failed")
        logger.log_command(spoken_text, "Failed", "Command not recognized")
        
        if best_suggestion:
            return False, f"Command not recognized. Did you mean '{best_suggestion}'?"
            
        return False, "Command not recognized"

