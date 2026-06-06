from ai.memory_manager import MemoryManager
from ai.gemini_client import GeminiClient
from utils.logger import logger

class ContextManager:
    def __init__(self, gemini_client: GeminiClient, memory_manager: MemoryManager):
        self.gemini_client = gemini_client
        self.memory_manager = memory_manager

    def resolve_context(self, current_input: str) -> str:
        """
        Analyzes the current user input in combination with recent history
        to resolve pronouns and references (e.g. "open it" -> "open chrome" or "close it" -> "close chrome").
        """
        history = self.memory_manager.get_recent_history(limit=5)
        if not history:
            return current_input

        # Fast rule check to check if pronoun replacement is likely needed
        pronoun_indicators = ["it", "that", "them", "there", "this", "him", "her"]
        words = current_input.lower().split()
        needs_resolution = any(w in pronoun_indicators for w in words)
        
        if not needs_resolution:
            return current_input

        # Assemble recent conversation context
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
                logger.log_command(current_input, "Success", f"Context resolved to: '{resolved_clean}'")
                return resolved_clean
                
        # Simple heuristic fallback
        return self._heuristic_fallback(current_input, history)

    def _heuristic_fallback(self, current_input: str, history: list) -> str:
        """Simple rule-based fallback to find the last mentioned application or target in history."""
        input_lower = current_input.lower().strip()
        
        # Look for "it" reference (e.g., "close it" or "open it")
        if input_lower in ["close it", "open it", "stop it", "run it", "launch it"]:
            # Traverse history backward to find the last app mentioned
            for item in reversed(history):
                msg = item["message"].lower()
                # If we find "opening <app>" or "launching <app>", or if user asked to "open <app>"
                for prefix in ["open ", "launch ", "start ", "run "]:
                    if prefix in msg:
                        words = msg.split(prefix)
                        if len(words) > 1:
                            target = words[1].strip()
                            # Strip common verbs/symbols
                            target = target.replace("!", "").replace(".", "").strip()
                            verb = input_lower.split()[0] # e.g. "close" or "open"
                            return f"{verb} {target}"
        return current_input
