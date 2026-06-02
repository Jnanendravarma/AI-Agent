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

    # Continuous listening and processing loop
    try:
        while True:
            # Step 1: Listen for voice input (or keyboard fallback)
            command = listener.listen()
            
            # If the command is empty, just continue listening
            if not command:
                continue
                
            # Step 2: Handle local exit commands directly if needed, or pass to executor
            # This ensures clean shutdown even if config fails
            cmd_lower = command.lower().strip()
            if cmd_lower in ["stop assistant", "exit assistant", "shutdown assistant"]:
                goodbye = "Shutting down the assistant. Goodbye!"
                speaker.speak(goodbye)
                logger.log_command(command, "Success", "Clean exit triggered")
                break

            # Step 3: Match and execute command using the dynamic command engine
            success, response = executor.execute(command)
            
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
