import sys
import os
import time
import datetime
import re
import keyboard

from voice.listener import VoiceListener
from utils.response_manager import response_manager
from engine.command_executor import CommandExecutor
from utils.logger import logger
from utils.tray_indicator import tray_indicator
from utils.preferences_manager import preferences_manager
from utils.dashboard_server import DashboardServer, set_executor_reference

def main():
    print("=" * 60)
    print("      WINDOWS VOICE-CONTROLLED DESKTOP AUTOMATION AGENT")
    print("=" * 60)
    
    # 1. Initialize System Tray Status Icon
    tray_indicator.start()
    tray_indicator.set_state("sleeping")

    # 2. Initialize Command Executor
    try:
        executor = CommandExecutor()
        # Register references for dashboard and scheduler
        set_executor_reference(executor)
        
        from services.scheduler_service import SchedulerService
        scheduler = SchedulerService(executor)
        
        listener = VoiceListener()
    except Exception as e:
        logger.log_error(f"Failed to bootstrap assistant components: {e}")
        tray_indicator.set_state("error")
        sys.exit(1)

    # 3. Start Dashboard Server on Port 8000
    dashboard_server = DashboardServer(port=8000)
    dashboard_server.start()

    # 4. Initial Assistant Smart Greeting based on Clock time
    hour = datetime.datetime.now().hour
    username = preferences_manager.get("username", "Jnanendra")
    if hour < 12:
        greeting_prefix = "Good morning"
    elif hour < 17:
        greeting_prefix = "Good afternoon"
    elif hour < 21:
        greeting_prefix = "Good evening"
    else:
        greeting_prefix = "Good night"
        
    greeting = f"{greeting_prefix} {username}. Desktop Automation Assistant is initialized and ready."
    response_manager.respond(greeting)

    # 5. Continuous listening and processing loop
    try:
        while True:
            command = ""
            # Step 1: Wait for wake word if in voice mode and wake word is enabled, and NOT in chat mode
            if not executor.in_chat_mode:
                if not listener.use_keyboard_fallback and listener.wake_word_enabled:
                    detected, remaining = listener.wait_for_wake_word()
                    if detected:
                        if remaining:
                            # Mode 2: Wake word + command in the same sentence
                            command = remaining
                        else:
                            # Mode 1: Wake word only
                            response_manager.respond("Yes, how can I help you?")
                            command = listener.listen()
                else:
                    # Text Mode / Keyboard fallback
                    command = listener.listen()
            else:
                # Active Chat Mode: directly listen without wake word
                command = listener.listen()
            
            if not command:
                time.sleep(0.1)
                continue
                
            cmd_lower = command.lower().strip()

            # Handle local exit commands directly
            if cmd_lower in ["stop assistant", "exit assistant", "shutdown assistant"]:
                goodbye = "Shutting down the assistant. Goodbye!"
                response_manager.respond(goodbye)
                logger.log_command(command, "Success", "Clean exit triggered")
                break

            # Handle exiting chat mode
            if executor.in_chat_mode and cmd_lower in ["exit chat", "stop chat", "exit chat mode", "stop chat mode"]:
                executor.in_chat_mode = False
                response_manager.respond("Exiting chat mode. Returning to standard assistant.")
                continue

            # Step 2: Parse and sequence multiple commands
            sub_commands = []
            if cmd_lower.startswith(("search ", "google ", "find ")):
                # Avoid splitting search keywords
                sub_commands = [command]
            else:
                # Split by "and", "then", or commas
                parts = re.split(r'\s+and\s+|\s+then\s+|,\s*', command)
                parts = [p.strip() for p in parts if p.strip()]
                
                last_verb = ""
                action_verbs = ["open", "launch", "start", "run", "close", "terminate", "exit", "kill", "stop", "search", "google", "find", "minimize", "maximize", "restore", "mute", "unmute"]
                
                for p in parts:
                    words = p.split()
                    if not words:
                        continue
                    first_word = words[0].lower()
                    if first_word in action_verbs:
                        last_verb = first_word
                        sub_commands.append(p)
                    else:
                        # Inherit preceding verb (e.g. "open Chrome and VS Code" -> "open Chrome" + "open VS Code")
                        if last_verb:
                            sub_commands.append(f"{last_verb} {p}")
                        else:
                            sub_commands.append(p)

            # Step 3: Run all sub-commands sequentially
            tray_indicator.set_state("processing")
            for sub_cmd in sub_commands:
                success, response = executor.execute(sub_cmd)
                if response:
                    response_manager.respond(response)
                    
            tray_indicator.set_state("sleeping")
            time.sleep(0.1)
            
    except KeyboardInterrupt:
        print("\nKeyboard Interrupt detected.")
        response_manager.respond("Exiting due to user interruption. Goodbye!")
    except Exception as e:
        logger.log_error(f"Fatal error in main orchestrator loop: {e}")
        response_manager.respond("A fatal error occurred. Shutting down.")
    finally:
        # Shut down servers
        try:
            dashboard_server.stop()
            scheduler.stop()
        except Exception:
            pass
        tray_indicator.set_state("sleeping")
        print("\n" + "=" * 60)
        print("                 ASSISTANT SESSION TERMINATED")
        print("=" * 60)

if __name__ == "__main__":
    main()
