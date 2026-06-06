import json
from ai.gemini_client import GeminiClient
from utils.logger import logger

class IntentClassifier:
    def __init__(self, gemini_client: GeminiClient):
        self.gemini_client = gemini_client
        self.intents = [
            "open_application",
            "close_application",
            "search_web",
            "search_youtube",
            "workflow_execution",
            "system_control",
            "volume_control",
            "brightness_control",
            "chat_mode",
            "task_planning",
            "document_analysis",
            "screenshot_analysis"
        ]

    def classify(self, user_input: str) -> dict:
        """
        Classifies user input using Gemini with fallback rule matching.
        Returns a dict: {"intent": str, "entities": dict}
        """
        # Hard check for starting chat mode explicitly
        input_clean = user_input.lower().strip()
        if input_clean == "start chat mode":
            return {"intent": "chat_mode", "entities": {"chat_command": "start"}}

        prompt = f"""
You are an intent classifier for a desktop automation AI agent.
Analyze the user command and classify it into exactly one of these intents:
{self.intents}

Also extract key entities (e.g. app_name, search_query, level/value for volume/brightness, file_path, or project_name).

Respond ONLY with a JSON object in this exact schema:
{{
  "intent": "intent_name",
  "entities": {{
    "app_name": "extracted application name",
    "search_query": "search text",
    "level": "volume or brightness level (integer or increment/decrement if spoken)",
    "file_path": "extracted file name or path",
    "project_name": "extracted project or workspace name"
  }}
}}

Ensure that "intent" is exactly one of the values listed above.
Example user query: "I need Chrome"
Response:
{{
  "intent": "open_application",
  "entities": {{
    "app_name": "chrome"
  }}
}}

Example user query: "what error is on my screen"
Response:
{{
  "intent": "screenshot_analysis",
  "entities": {{}}
}}

Example user query: "summarize this resume pdf"
Response:
{{
  "intent": "document_analysis",
  "entities": {{
    "file_path": "resume"
  }}
}}

Example user query: "prepare my coding environment"
Response:
{{
  "intent": "task_planning",
  "entities": {{
    "project_name": "coding environment"
  }}
}}

Example user query: "explain React hooks"
Response:
{{
  "intent": "chat_mode",
  "entities": {{
    "search_query": "explain React hooks"
  }}
}}

User query to classify: "{user_input}"
"""
        response, err = self.gemini_client.generate_content(prompt, model_name="gemini-2.5-flash")
        
        if response and not err:
            try:
                # Strip markdown code blocks if present
                clean_json = response.strip()
                if clean_json.startswith("```json"):
                    clean_json = clean_json[7:]
                if clean_json.endswith("```"):
                    clean_json = clean_json[:-3]
                clean_json = clean_json.strip()
                
                result = json.loads(clean_json)
                if result.get("intent") in self.intents:
                    # Validate entities
                    if "entities" not in result:
                        result["entities"] = {}
                    return result
            except Exception as e:
                logger.log_error(f"Failed to parse Gemini intent response: {e}. Raw response: {response}")
                
        # Heuristic fallback if Gemini fails or is unconfigured
        return self._rule_based_fallback(input_clean)

    def _rule_based_fallback(self, text: str) -> dict:
        """Simple rule matching to identify standard commands if AI layer is offline."""
        logger.log_error(f"Falling back to rule-based intent classification for: '{text}'")
        
        # 1. Volume
        if any(w in text for w in ["volume", "mute", "unmute", "sound"]):
            # Extract number
            level = ""
            for word in text.split():
                if word.isdigit():
                    level = word
                    break
            return {"intent": "volume_control", "entities": {"level": level}}
            
        # 2. Brightness
        if "brightness" in text:
            level = ""
            for word in text.split():
                if word.isdigit():
                    level = word
                    break
            return {"intent": "brightness_control", "entities": {"level": level}}

        # 2.5 Diagnostics and History Control Fallback
        diagnostics_keywords = [
            "battery", "system information", "system info", "cpu usage", "ram usage", 
            "memory usage", "disk usage", "disk space", "pc specs", "specs", 
            "temperature", "temp status", "show history", "recent commands", "history"
        ]
        if any(keyword in text for keyword in diagnostics_keywords):
            return {"intent": "system_control", "entities": {}}

        # 3. Screenshot
        if any(w in text for w in ["screenshot", "capture screen", "analyze screen", "analyze my screen"]):
            return {"intent": "screenshot_analysis", "entities": {}}

        # 4. PDF
        if any(w in text for w in ["pdf", "document", "summarize"]):
            return {"intent": "document_analysis", "entities": {}}

        # 5. YouTube Search
        if "youtube" in text:
            return {"intent": "search_youtube", "entities": {"search_query": text.replace("youtube", "").strip()}}

        # 6. Web Search
        if any(text.startswith(prefix) for prefix in ["search ", "google ", "find "]):
            return {"intent": "search_web", "entities": {"search_query": text}}

        # 7. Workflow
        if "workflow" in text or "setup" in text:
            return {"intent": "workflow_execution", "entities": {}}

        # 8. Open App
        for verb in ["open", "launch", "start", "run"]:
            if text.startswith(verb + " "):
                return {"intent": "open_application", "entities": {"app_name": text[len(verb)+1:].strip()}}

        # 9. Close App
        for verb in ["close", "terminate", "exit", "kill", "stop"]:
            if text.startswith(verb + " "):
                return {"intent": "close_application", "entities": {"app_name": text[len(verb)+1:].strip()}}

        # Default
        return {"intent": "chat_mode", "entities": {"search_query": text}}
