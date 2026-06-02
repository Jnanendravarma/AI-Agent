import re
from utils.logger import logger

PYCAW_AVAILABLE = False
try:
    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
    from ctypes import cast, POINTER
    from comtypes import CLSCTX_ALL
    PYCAW_AVAILABLE = True
except ImportError:
    logger.log_error("pycaw or comtypes is not installed. Volume control service will be disabled.")

class VolumeService:
    @staticmethod
    def _get_volume_control():
        if not PYCAW_AVAILABLE:
            return None
        try:
            # Under some environments, COM initialization is required
            import pythoncom
            pythoncom.CoInitialize()
        except Exception:
            pass
            
        try:
            devices = AudioUtilities.GetSpeakers()
            if not devices:
                return None
            if hasattr(devices, "EndpointVolume"):
                return devices.EndpointVolume
            interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            return cast(interface, POINTER(IAudioEndpointVolume))
        except Exception as e:
            logger.log_error(f"Failed to access system speaker endpoint: {e}")
            return None

    @classmethod
    def execute_volume_command(cls, command_text: str) -> tuple[bool, str]:
        """
        Parses and executes volume control commands.
        Commands:
        - "increase volume" / "raise volume" / "volume up"
        - "decrease volume" / "lower volume" / "volume down"
        - "mute volume" / "mute" / "turn sound off"
        - "unmute volume" / "unmute" / "turn sound on"
        - "set volume to X percent" / "set volume to X"
        """
        cmd_clean = command_text.strip().lower()
        volume_ctrl = cls._get_volume_control()
        
        if not volume_ctrl:
            return False, "Audio control is unavailable or no speakers are connected on this system."

        try:
            # 1. Mute Commands
            if "unmute" in cmd_clean or "sound on" in cmd_clean:
                volume_ctrl.SetMute(0, None)
                return True, "Sound unmuted"
            elif "mute" in cmd_clean or "sound off" in cmd_clean:
                volume_ctrl.SetMute(1, None)
                return True, "Sound muted"

            # 2. Set Volume Percentage Commands
            match = re.search(r"set\s+volume\s+to\s+(\d+)", cmd_clean)
            if not match:
                match = re.search(r"volume\s+(\d+)\s*percent", cmd_clean)
            if not match:
                match = re.search(r"volume\s+(\d+)", cmd_clean)
                
            if match:
                level = int(match.group(1))
                level = max(0, min(100, level))  # Clamp to [0, 100]
                volume_ctrl.SetMasterVolumeLevelScalar(level / 100.0, None)
                # Unmute automatically when setting volume
                volume_ctrl.SetMute(0, None)
                return True, f"Volume set to {level} percent"

            # 3. Increase Volume Commands
            if "increase" in cmd_clean or "raise" in cmd_clean or "up" in cmd_clean:
                current = volume_ctrl.GetMasterVolumeLevelScalar()
                new_vol = min(1.0, current + 0.10)  # Increase by 10%
                volume_ctrl.SetMasterVolumeLevelScalar(new_vol, None)
                volume_ctrl.SetMute(0, None)
                return True, f"Volume increased to {int(new_vol * 100)} percent"

            # 4. Decrease Volume Commands
            if "decrease" in cmd_clean or "lower" in cmd_clean or "down" in cmd_clean:
                current = volume_ctrl.GetMasterVolumeLevelScalar()
                new_vol = max(0.0, current - 0.10)  # Decrease by 10%
                volume_ctrl.SetMasterVolumeLevelScalar(new_vol, None)
                return True, f"Volume decreased to {int(new_vol * 100)} percent"

            return False, "Could not determine the volume action. Try saying increase volume, decrease volume, or set volume to 50 percent."
            
        except Exception as e:
            logger.log_error(f"Error executing volume command: {e}")
            return False, f"Error occurred while controlling volume: {str(e)}"
