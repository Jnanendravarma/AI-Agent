import json
import re
from utils.logger import logger

class IntentClassifier:
    def __init__(self, gemini_client=None):
        self.gemini_client = gemini_client
        self.intents = [
            "OPEN_APPLICATION",
            "CLOSE_APPLICATION",
            "OPEN_WEBSITE",
            "CLOSE_WEBSITE",
            "WINDOW_CONTROL",
            "SYSTEM_CONTROL",
            "SEARCH",
            "CHAT",
            "TASK_PLANNER"
        ]

    def _fuzzy_match_local(self, query: str, choices: list[str], threshold: int = 75) -> tuple[str, int]:
        """Fuzzy string matching helper using RapidFuzz WRatio."""
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
                return matches[0], 80
        return None, 0

    def classify_locally(self, user_input: str, discovered_apps: list = None, commands_lookup: list = None) -> dict:
        """
        Classifies user input locally using strict rules and fuzzy matching choices.
        Runs entirely offline. NO API calls.
        """
        text_lower = user_input.lower().strip()
        for char in "?.,!":
            text_lower = text_lower.replace(char, "")
        text_lower = text_lower.strip()

        # 1. Chat Mode Toggles
        chat_start_triggers = ["start chat mode", "start chat", "enable chat", "chat mode"]
        chat_stop_triggers = ["exit chat mode", "exit chat", "stop chat mode", "stop chat"]
        
        if text_lower in chat_start_triggers:
            return {"intent": "CHAT", "entities": {"chat_command": "start"}}
        if text_lower in chat_stop_triggers:
            return {"intent": "CHAT", "entities": {"chat_command": "stop"}}

        # Fuzzy check for chat commands
        if any(w in text_lower for w in ["chat", "chart", "chate"]):
            best_start, start_score = self._fuzzy_match_local(text_lower, chat_start_triggers, threshold=80)
            best_stop, stop_score = self._fuzzy_match_local(text_lower, chat_stop_triggers, threshold=80)
            if start_score >= 80:
                return {"intent": "CHAT", "entities": {"chat_command": "start"}}
            if stop_score >= 80:
                return {"intent": "CHAT", "entities": {"chat_command": "stop"}}

        # 2. Window Commands
        window_verbs = ["minimize", "maximize", "restore", "close active", "close window", "bring to front", "switch window", "show desktop", "bring window"]
        if any(v in text_lower for v in window_verbs) or "window" in text_lower:
            action = "minimize"
            if "maximize" in text_lower:
                action = "maximize"
            elif "restore" in text_lower:
                action = "restore"
            elif "close" in text_lower:
                action = "close_active"
            elif "desktop" in text_lower:
                action = "show_desktop"
            elif "switch" in text_lower:
                action = "switch_window"
            elif "front" in text_lower or "bring" in text_lower:
                action = "bring_to_front"
                
            # Extract target for bring_to_front
            target = ""
            if action == "bring_to_front":
                words = text_lower.split()
                if "front" in words:
                    idx = words.index("front")
                    if idx > 2 and words[idx-1] == "to" and words[idx-2] == "bring":
                        # bring X to front
                        target = words[idx-3]
                elif "window" in words:
                    idx = words.index("window")
                    if idx + 1 < len(words):
                        target = words[idx+1]
            return {"intent": "WINDOW_CONTROL", "entities": {"action": action, "target": target}}

        # 3. System Control / Diagnostics
        system_keywords = [
            "battery", "system information", "system info", "cpu usage", "ram usage", 
            "memory usage", "disk usage", "disk space", "pc specs", "specs", 
            "temperature", "temp status", "show history", "recent commands", "history",
            "volume", "mute", "unmute", "sound", "brightness"
        ]
        if any(kw in text_lower for kw in system_keywords):
            # Extract level if present (e.g. "volume 50")
            level = ""
            for word in text_lower.split():
                if word.isdigit():
                    level = word
                    break
            return {"intent": "SYSTEM_CONTROL", "entities": {"level": level}}

        # 4. Search Commands
        if any(text_lower.startswith(prefix) for prefix in ["search ", "google ", "find "]):
            # If it's a search but doesn't mention applications or websites to open/close
            if not any(w in text_lower for w in ["open", "close", "launch", "exit", "terminate"]):
                query = re.sub(r'^(search|google|find)\s+', '', text_lower).strip()
                return {"intent": "SEARCH", "entities": {"query": query}}

        # 5. Open/Close Verbs & Targets classification
        open_verbs = ["open", "launch", "start", "run", "go to", "kholo", "open chey", "open cheyyi", "chalu karo", "chalu"]
        close_verbs = ["close", "terminate", "exit", "kill", "stop", "band kar", "band karo", "band", "close chey", "close cheyyi"]
        
        is_open = any(f"{v} " in f"{text_lower} " for v in open_verbs)
        is_close = any(f"{v} " in f"{text_lower} " for v in close_verbs)

        # Predefined target collections
        websites = ["youtube", "github", "google", "stackoverflow", "leetcode", "gmail", "chatgpt", "gemini"]
        apps = ["chrome", "edge", "vs code", "vscode", "visual studio code", "spotify", "discord", "notepad", "calculator", "explorer", "paint", "mspaint"]
        
        if discovered_apps:
            for app in discovered_apps:
                if app not in apps:
                    apps.append(app)
                    
        # Extract candidate target word after verb
        candidate_target = ""
        for v in sorted(open_verbs + close_verbs, key=len, reverse=True):
            if text_lower.startswith(f"{v} "):
                candidate_target = text_lower[len(v):].strip()
                break
                
        if not candidate_target:
            # Maybe the verb is elsewhere or last
            candidate_target = text_lower

        # Strip common modifiers
        candidate_target = candidate_target.replace("website", "").replace("site", "").replace("page", "").strip()

        # Check if target maps to a website
        best_site, site_score = self._fuzzy_match_local(candidate_target, websites, threshold=75)
        # Check if target maps to an app
        best_app, app_score = self._fuzzy_match_local(candidate_target, apps, threshold=75)

        # Check if the target explicitly ends with standard domain suffixes or mentions website
        is_explicit_site = any(suffix in candidate_target for suffix in [".com", ".org", ".net", ".in"]) or "website" in text_lower or "site" in text_lower

        if is_explicit_site or (best_site and site_score >= app_score):
            site_target = best_site if best_site else candidate_target
            if is_close:
                return {"intent": "CLOSE_WEBSITE", "entities": {"target": site_target}}
            else:
                return {"intent": "OPEN_WEBSITE", "entities": {"target": site_target}}
        
        elif best_app:
            if is_close:
                return {"intent": "CLOSE_APPLICATION", "entities": {"target": best_app}}
            else:
                return {"intent": "OPEN_APPLICATION", "entities": {"target": best_app}}

        # 6. Task Planner / Interview Prep
        if any(w in text_lower for w in ["plan", "schedule prepare", "interview", "prep", "prepare"]):
            return {"intent": "TASK_PLANNER", "entities": {"query": user_input}}

        # Default fallback to Chat / Educational
        return {"intent": "CHAT", "entities": {"query": user_input}}
