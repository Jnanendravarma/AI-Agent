import os
import json
import webbrowser
import time
from utils.logger import logger
from controllers.app_controller import AppController
from controllers.window_controller import WindowController

class WorkflowService:
    @staticmethod
    def _load_workflows() -> dict:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        workflows_path = os.path.join(base_dir, "workflows", "workflows.json")
        
        if not os.path.exists(workflows_path):
            logger.log_error(f"Workflows config file not found at {workflows_path}")
            return {}
            
        try:
            with open(workflows_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.log_error(f"Failed to read workflows.json: {e}")
            return {}

    @classmethod
    def execute_workflow(cls, command_text: str) -> tuple[bool, str]:
        """
        Loads workflows and runs matching automation routine.
        Commands:
        - "open coding setup"
        - "run mern setup"
        - "activate meeting setup"
        """
        cmd_clean = command_text.strip().lower()
        workflows = cls._load_workflows()
        
        if not workflows:
            return False, "Workflows database is empty or not configured."

        # Find matching workflow
        target_workflow = None
        workflow_key_found = ""
        
        for w_name in workflows.keys():
            # If workflow name is contained in the spoken command
            if w_name in cmd_clean:
                target_workflow = workflows[w_name]
                workflow_key_found = w_name
                break

        if not target_workflow:
            return False, "Workflow not recognized. Available setups: " + ", ".join(workflows.keys())

        logger.log_command(command_text, "Success", f"Starting workflow: {workflow_key_found}")
        
        success_count = 0
        total_steps = len(target_workflow)
        
        for step in target_workflow:
            step_type = step.get("type", "").lower()
            try:
                if step_type == "application":
                    cmd = step.get("command")
                    if AppController.open_app(cmd):
                        success_count += 1
                        
                elif step_type == "website":
                    url = step.get("url")
                    webbrowser.open(url)
                    success_count += 1
                    
                elif step_type == "window":
                    action = step.get("action")
                    if WindowController.execute_action(action):
                        success_count += 1
                        
                elif step_type == "folder":
                    path = os.path.expanduser(step.get("path", ""))
                    if os.path.exists(path):
                        os.startfile(path)
                        success_count += 1
                        
                # Brief sleep between steps for smooth execution
                time.sleep(0.3)
            except Exception as step_err:
                logger.log_error(f"Error executing workflow step ({step}): {step_err}")

        response = f"Workflow {workflow_key_found} executed. Successfully completed {success_count} out of {total_steps} actions."
        return True, response
