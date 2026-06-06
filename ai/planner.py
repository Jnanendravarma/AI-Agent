import json
from ai.gemini_client import GeminiClient
from utils.logger import logger

class TaskPlanner:
    def __init__(self, gemini_client: GeminiClient):
        self.gemini_client = gemini_client

    def generate_plan(self, task_description: str, discovered_apps: list, configured_folders: list) -> list:
        """
        Uses Gemini to plan a sequence of discrete automation steps to accomplish a complex user request.
        Returns a list of actions, e.g. [{"type": "open_app", "target": "chrome"}, {"type": "open_url", "target": "https://github.com"}]
        """
        prompt = f"""
You are the Task Planner component of a desktop automation AI agent.
Your objective is to satisfy the user's high-level goal by breaking it down into a list of sequential actions.

User's Request: "{task_description}"

Available Discovered Applications:
{discovered_apps}

Available Custom folders:
{configured_folders}

You can suggest actions using these exact JSON formats:
1. Open a system/discovered application:
{{"type": "open_app", "target": "application name or path"}}
2. Open a website URL:
{{"type": "open_url", "target": "URL string (e.g., https://github.com)"}}
3. Open a folder directory:
{{"type": "open_folder", "target": "folder name or path"}}

Example Request: "Prepare my coding environment"
Output:
[
  {{"type": "open_app", "target": "visual studio code"}},
  {{"type": "open_app", "target": "chrome"}},
  {{"type": "open_url", "target": "https://github.com"}},
  {{"type": "open_app", "target": "cmd"}}
]

Return ONLY the JSON list of actions. Do not provide code blocks, markdown wrapper, explanations, or comments.
If the goal is not decomposable or simple, return a list containing a single action to open the most relevant item.
"""
        response, err = self.gemini_client.generate_content(prompt, model_name="gemini-2.5-flash")
        
        if response and not err:
            try:
                clean_json = response.strip()
                if clean_json.startswith("```json"):
                    clean_json = clean_json[7:]
                if clean_json.endswith("```"):
                    clean_json = clean_json[:-3]
                clean_json = clean_json.strip()
                
                actions = json.loads(clean_json)
                if isinstance(actions, list):
                    logger.log_command(task_description, "Success", f"Generated plan containing {len(actions)} steps.")
                    return actions
            except Exception as e:
                logger.log_error(f"Failed to parse task plan JSON: {e}. Raw response: {response}")
                
        # Basic heuristic fallback
        return self._heuristic_fallback(task_description.lower())

    def _heuristic_fallback(self, task: str) -> list:
        """Simple rule-based planner fallback if AI layer is offline."""
        actions = []
        if "coding" in task or "develop" in task or "programming" in task:
            actions.append({"type": "open_app", "target": "visual studio code"})
            actions.append({"type": "open_app", "target": "chrome"})
            actions.append({"type": "open_url", "target": "https://github.com"})
        elif "browser" in task or "web" in task:
            actions.append({"type": "open_app", "target": "chrome"})
        elif "note" in task or "write" in task:
            actions.append({"type": "open_app", "target": "notepad"})
        return actions
