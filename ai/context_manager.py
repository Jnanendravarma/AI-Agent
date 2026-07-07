import re
from ai.memory_manager import MemoryManager
from ai.gemini_client import GeminiClient
from utils.logger import logger

class ContextManager:
    def __init__(self, gemini_client: GeminiClient, memory_manager: MemoryManager):
        self.gemini_client = gemini_client
        self.memory_manager = memory_manager

    def resolve_context(self, current_input: str, force_local: bool = False) -> str:
        """
        Analyzes the current user input in combination with recent history
        to resolve pronouns and references (e.g. "open it" -> "open chrome" or "close it" -> "close chrome").
        """
        history = self.memory_manager.get_recent_history(limit=5)
        if not history:
            return current_input

        # Check if pronoun resolution is likely needed
        pronoun_indicators = ["it", "this", "that", "them"]
        words = current_input.lower().split()
        needs_resolution = any(w in pronoun_indicators for w in words)
        
        if not needs_resolution:
            return current_input

        # 1. Attempt Local/Heuristic Resolution first to respect the Hybrid Architecture rules
        local_resolved = self.resolve_context_locally(current_input, history)
        if local_resolved != current_input:
            logger.log_command(current_input, "Success", f"Context resolved locally to: '{local_resolved}'")
            return local_resolved

        if force_local:
            return current_input

        # 2. Online/Gemini Resolution (only if not forced local and in Chat Mode)
        history_str = ""
        for item in history:
            role_name = "User" if item["role"] == "user" else "Assistant"
            history_str += f"{role_name}: {item['message']}\n"
            
        prompt = f"""
You are the context resolution component of a desktop AI agent.
Your task is to rewrite the User's Latest Command to resolve any pronoun references (like 'it', 'that', 'them') using the recent conversation history.

Recent Conversation History:
{history_str}

User's Latest Command: "{current_input}"

If a pronoun like 'it' is referring to an application, file, directory, website, or query mentioned in the history, replace that pronoun with the specific name.
Examples:
History:
User: Open Chrome
Assistant: Opening Chrome
User's Latest Command: "close it" -> Output: "close chrome"

History:
User: Search for EventHub project
Assistant: Found EventHub folder
User's Latest Command: "open it in vs code" -> Output: "open EventHub folder in vs code"

Output ONLY the resolved command string on a single line. Do not add quotes, explanation, or markdown formatting. If no pronouns require resolution, output the command exactly as it is.
"""
        resolved, err = self.gemini_client.generate_content(prompt, model_name="gemini-2.5-flash")
        if resolved and not err:
            resolved_clean = resolved.strip().strip('"')
            if resolved_clean:
                logger.log_command(current_input, "Success", f"Context resolved via Gemini to: '{resolved_clean}'")
                return resolved_clean
                
        # Simple heuristic fallback
        return self._heuristic_fallback(current_input, history)

    def resolve_context_locally(self, current_input: str, history: list) -> str:
        """Resolves pronouns locally without using Gemini for automation commands."""
        input_lower = current_input.lower().strip()
        for char in "?.,!":
            input_lower = input_lower.replace(char, "")
        input_lower = input_lower.strip()
        
        pronouns = ["it", "this", "that", "them"]
        words = input_lower.split()
        if not any(p in words for p in pronouns):
            return current_input

        # Handle volume/mute references (e.g. "mute it" -> "mute volume")
        if any(w in words for w in ["mute", "unmute"]):
            return input_lower.replace("it", "volume").replace("this", "volume").replace("that", "volume").replace("them", "volume")

        # Handle window references (e.g. "minimize it" -> "minimize window")
        if any(w in words for w in ["minimize", "maximize", "restore", "close"]):
            # If the user says "close it" we prefer closing the last app, otherwise default to "window"
            if "close" in words:
                pass
            else:
                return input_lower.replace("it", "window").replace("this", "window").replace("that", "window").replace("them", "window")

        # Find the last app/target mentioned in the history
        last_target = None
        for item in reversed(history):
            msg = item["message"].lower()
            # Clean msg
            msg = msg.replace("opening", "").replace("closing", "").replace("opening discovered application", "").strip()
            # Look for common open/close/run verbs
            for verb in ["open ", "launch ", "start ", "run ", "close ", "terminate ", "kill ", "stop ", "to "]:
                if verb in msg:
                    parts = msg.split(verb)
                    if len(parts) > 1:
                        candidate = parts[1].strip()
                        candidate = re.sub(r'^[,\s!?.-]+', '', candidate)
                        candidate = candidate.replace("!", "").replace(".", "").strip()
                        # Avoid matching pronouns or generic words
                        if candidate and candidate not in ["it", "this", "that", "them", "volume", "window", "assistant"]:
                            last_target = candidate
                            break
            if last_target:
                break
                
        if last_target:
            resolved_words = []
            for w in words:
                if w in pronouns:
                    resolved_words.append(last_target)
                else:
                    resolved_words.append(w)
            return " ".join(resolved_words)
            
        return current_input

    def _heuristic_fallback(self, current_input: str, history: list) -> str:
        """Simple rule-based fallback to find the last mentioned application or target in history."""
        input_lower = current_input.lower().strip()
        
        if input_lower in ["close it", "open it", "stop it", "run it", "launch it"]:
            for item in reversed(history):
                msg = item["message"].lower()
                for prefix in ["open ", "launch ", "start ", "run "]:
                    if prefix in msg:
                        words = msg.split(prefix)
                        if len(words) > 1:
                            target = words[1].strip()
                            target = target.replace("!", "").replace(".", "").strip()
                            verb = input_lower.split()[0]
                            return f"{verb} {target}"
        return current_input
