import re
from utils.logger import logger

SBC_AVAILABLE = False
try:
    import screen_brightness_control as sbc
    SBC_AVAILABLE = True
except ImportError:
    logger.log_error("screen-brightness-control is not installed. Brightness control service is disabled.")

class BrightnessService:
    @classmethod
    def execute_brightness_command(cls, command_text: str) -> tuple[bool, str]:
        """
        Parses and executes brightness control commands.
        Commands:
        - "increase brightness" / "raise brightness" / "brightness up"
        - "decrease brightness" / "lower brightness" / "brightness down"
        - "set brightness to X percent" / "set brightness to X"
        - "set brightness to maximum" / "max brightness"
        """
        if not SBC_AVAILABLE:
            return False, "Screen brightness control library is unavailable."

        cmd_clean = command_text.strip().lower()

        try:
            # Check if there is an active monitor that supports brightness control
            try:
                current_brightness_list = sbc.get_brightness()
                if not current_brightness_list:
                    return False, "No compatible monitors found that support brightness control."
                # Take first monitor's brightness
                current_val = current_brightness_list[0]
            except Exception as monitor_err:
                logger.log_error(f"Error checking monitors: {monitor_err}")
                return False, "This display monitor does not support software brightness controls."

            # 1. Max Brightness
            if "maximum" in cmd_clean or "max" in cmd_clean:
                sbc.set_brightness(100)
                return True, "Brightness set to maximum"

            # 2. Set Specific Brightness
            match = re.search(r"set\s+brightness\s+to\s+(\d+)", cmd_clean)
            if not match:
                match = re.search(r"brightness\s+(\d+)\s*percent", cmd_clean)
            if not match:
                match = re.search(r"brightness\s+(\d+)", cmd_clean)
                
            if match:
                level = int(match.group(1))
                level = max(0, min(100, level))  # Clamp to [0, 100]
                sbc.set_brightness(level)
                return True, f"Brightness set to {level} percent"

            # 3. Increase Brightness
            if "increase" in cmd_clean or "raise" in cmd_clean or "up" in cmd_clean:
                new_brightness = min(100, current_val + 10)
                sbc.set_brightness(new_brightness)
                return True, f"Brightness increased to {new_brightness} percent"

            # 4. Decrease Brightness
            if "decrease" in cmd_clean or "lower" in cmd_clean or "down" in cmd_clean:
                new_brightness = max(0, current_val - 10)
                sbc.set_brightness(new_brightness)
                return True, f"Brightness decreased to {new_brightness} percent"

            return False, "Could not determine the brightness action. Try saying increase brightness, decrease brightness, or set brightness to 70 percent."

        except Exception as e:
            logger.log_error(f"Brightness control operation failed: {e}")
            return False, f"Failed to control screen brightness: {str(e)}"
