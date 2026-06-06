import os
import json
from ai.gemini_client import GeminiClient
from utils.logger import logger

class WorkflowGenerator:
    def __init__(self, gemini_client: GeminiClient):
        self.gemini_client = gemini_client

    def generate_dynamic_workflow(self, project_name: str, discovered_apps: dict) -> list:
        """
        Dynamically analyzes the directory matching project_name and generates a tailored workflow.
        Returns a list of actions to run.
        """
        logger.log_command(f"Generate dynamic workflow for project '{project_name}'", "In Progress")
        
        project_folder = self._find_project_folder(project_name)
        project_details = "No local project folder discovered."
        git_repo = False
        
        if project_folder:
            project_details = self._analyze_folder_contents(project_folder)
            git_repo = os.path.exists(os.path.join(project_folder, ".git"))
            logger.log_command(project_name, "Success", f"Found project folder: {project_folder}")
        else:
            logger.log_command(project_name, "Failed", "Could not locate project folder.")

        prompt = f"""
You are the Dynamic Workflow understanding assistant for a desktop agent.
The user wants to work on their project: "{project_name}"
Discovered Local Directory: "{project_folder or 'Not found'}"
Local Directory Content Analysis: {project_details}
Git Repository Present: {git_repo}

Suggest a set of actions to initialize or resume work on this project.
You can output actions using these exact forms:
- {{"type": "open_folder", "target": "<absolute_path_or_folder_name>"}}
- {{"type": "open_app", "target": "<application_name>"}}
- {{"type": "open_url", "target": "<url_link>"}}

Available Applications: {list(discovered_apps.keys())}

Note:
1. If a local directory is found, open it in File Explorer.
2. If it contains project code (e.g. Node, Python, Java), open VS Code (or visual studio code) on that directory.
3. If it is a web repository, suggest opening GitHub.
4. If it mentions database files (e.g., MongoDB, SQLite), open the DB client if available.

Output ONLY the JSON list of actions. No markdown blocks, comments, or explanations.
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
                    return actions
            except Exception as e:
                logger.log_error(f"Failed to parse dynamic workflow JSON: {e}")

        # Heuristic fallback if AI fails or no folder is found
        fallback_actions = []
        if project_folder:
            fallback_actions.append({"type": "open_folder", "target": project_folder})
            if "visual studio code" in discovered_apps:
                fallback_actions.append({"type": "open_app", "target": "visual studio code"})
            elif "vscode" in discovered_apps:
                fallback_actions.append({"type": "open_app", "target": "vscode"})
        return fallback_actions

    def _find_project_folder(self, project_name: str) -> str:
        """Searches user folders for a folder matching project_name (up to depth 2)."""
        search_paths = [
            os.path.expanduser("~/Desktop"),
            os.path.expanduser("~/Documents"),
            os.path.expanduser("~/Downloads"),
            os.path.expanduser("~/Projects")
        ]
        
        query = project_name.lower().strip()
        
        for base_path in search_paths:
            if not os.path.exists(base_path):
                continue
            try:
                for root, dirs, _ in os.walk(base_path):
                    # Check depth
                    depth = root[len(base_path):].count(os.sep)
                    if depth > 2:
                        dirs.clear() # do not walk deeper
                        continue
                    for d in dirs:
                        if query in d.lower():
                            return os.path.join(root, d)
            except Exception as e:
                logger.log_error(f"Error searching project folder: {e}")
        return None

    def _analyze_folder_contents(self, path: str) -> str:
        """Inspects folder files to guess project tech stack details."""
        try:
            files = os.listdir(path)
            files_lower = [f.lower() for f in files]
            
            indicators = []
            if "package.json" in files_lower:
                indicators.append("JavaScript/Node.js project")
            if "requirements.txt" in files_lower or "pyproject.toml" in files_lower:
                indicators.append("Python project")
            if "pom.xml" in files_lower:
                indicators.append("Java Maven project")
            if "go.mod" in files_lower:
                indicators.append("Go project")
            if "index.html" in files_lower:
                indicators.append("Frontend website project")
            if any("mongo" in f for f in files_lower):
                indicators.append("Database: MongoDB")
            
            if indicators:
                return f"Contains: {', '.join(indicators)}"
            return "Contains generic files."
        except Exception:
            return "Unable to read directory files."
