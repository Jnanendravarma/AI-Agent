import sys
import time
from voice.listener import VoiceListener
from voice.speaker import VoiceSpeaker
from engine.command_executor import CommandExecutor
from utils.logger import logger

def main():
    print("=" * 60)
    print("      WINDOWS VOICE-CONTROLLED DESKTOP AUTOMATION AGENT")
    print("=" * 60)
    
    # Initialize components
    try:
        speaker = VoiceSpeaker()
        listener = VoiceListener()
        executor = CommandExecutor()
    except Exception as e:
        logger.log_error(f"Failed to bootstrap assistant components: {e}")
        sys.exit(1)

    # Initial assistant greeting
    greeting = "Desktop Automation Assistant is initialized and ready."
    speaker.speak(greeting)

    # Track chat mode state
    in_chat_mode = False

    # Continuous listening and processing loop
    try:
        while True:
            # Step 1: Wait for wake word if voice mode is active, wake word is enabled, and NOT in chat mode
            if not in_chat_mode:
                if not listener.use_keyboard_fallback and listener.wake_word_enabled:
                    listener.wait_for_wake_word()
                    speaker.speak("Yes?")

            # Step 2: Listen for voice command or keyboard input
            command = listener.listen()
            
            # If the command is empty, just continue
            if not command:
                continue
                
            cmd_lower = command.lower().strip()

            # Handle exiting chat mode
            if in_chat_mode and cmd_lower in ["exit chat", "stop chat", "exit chat mode", "stop chat mode"]:
                in_chat_mode = False
                speaker.speak("Exiting chat mode. Returning to standard assistant.")
                continue

            # Handle local exit commands directly if needed
            if cmd_lower in ["stop assistant", "exit assistant", "shutdown assistant"]:
                goodbye = "Shutting down the assistant. Goodbye!"
                speaker.speak(goodbye)
                logger.log_command(command, "Success", "Clean exit triggered")
                break

            # Step 3: Match and execute command using the dynamic command engine
            success, response = executor.execute(command)

            # Check if user triggered chat mode to bypass wake word for next turn
            if "start chat mode" in cmd_lower:
                in_chat_mode = True
            
            # Step 4: Speak status / action confirmation back to the user
            if response:
                speaker.speak(response)
                
            # Short sleep to prevent CPU spiking in text fallback modes
            time.sleep(0.1)
            
    except KeyboardInterrupt:
        print("\nKeyboard Interrupt detected.")
        speaker.speak("Exiting due to user interruption. Goodbye!")
    except Exception as e:
        logger.log_error(f"Fatal error in main orchestrator loop: {e}")
        speaker.speak("A fatal error occurred. Shutting down.")
    finally:
        print("\n" + "=" * 60)
        print("                 ASSISTANT SESSION TERMINATED")
        print("=" * 60)

if __name__ == "__main__":
    main()

