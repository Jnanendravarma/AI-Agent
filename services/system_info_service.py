import platform
import psutil
from utils.logger import logger

class SystemInfoService:
    @staticmethod
    def get_battery_status() -> str:
        """Retrieves current battery percentage and charging state."""
        try:
            battery = psutil.sensors_battery()
            if battery is None:
                return "This system does not have a battery or battery status is unavailable."
            
            percent = battery.percent
            plugged = battery.power_plugged
            status = "charging" if plugged else "discharging"
            
            # Estimate remaining time
            secs = battery.secsleft
            if plugged:
                time_info = "and is plugged into power."
            elif secs == psutil.POWER_TIME_UNLIMITED:
                time_info = "and is not plugged in."
            elif secs == psutil.POWER_TIME_UNKNOWN:
                time_info = "and is running on battery."
            else:
                mins = secs // 60
                hours = mins // 60
                mins = mins % 60
                time_info = f"with approximately {hours} hours and {mins} minutes remaining."
                
            return f"Your battery is at {percent} percent, and is currently {status}, {time_info}"
        except Exception as e:
            logger.log_error(f"Error querying battery: {e}")
            return "Unable to retrieve battery status at this time."

    @staticmethod
    def get_system_info() -> str:
        """Retrieves operating system and CPU architecture details."""
        try:
            sys_info = platform.system()
            release = platform.release()
            version = platform.version()
            machine = platform.machine()
            processor = platform.processor()
            
            return f"This system is running {sys_info} version {release}, on an {machine} processor architecture. The specific processor is {processor}."
        except Exception as e:
            logger.log_error(f"Error querying system info: {e}")
            return "Unable to retrieve system specifications."

    @staticmethod
    def get_cpu_usage() -> str:
        """Calculates CPU usage percentage over a brief interval."""
        try:
            # Short 0.1s block to get an accurate reading
            usage = psutil.cpu_percent(interval=0.1)
            cores = psutil.cpu_count(logical=True)
            return f"Current CPU usage is at {usage} percent across {cores} logical processors."
        except Exception as e:
            logger.log_error(f"Error querying CPU usage: {e}")
            return "Unable to retrieve CPU usage."

    @staticmethod
    def get_ram_usage() -> str:
        """Retrieves RAM usage statistics."""
        try:
            mem = psutil.virtual_memory()
            used_gb = round(mem.used / (1024**3), 1)
            total_gb = round(mem.total / (1024**3), 1)
            return f"RAM usage is currently at {mem.percent} percent. You are using {used_gb} gigabytes out of {total_gb} gigabytes total memory."
        except Exception as e:
            logger.log_error(f"Error querying RAM usage: {e}")
            return "Unable to retrieve RAM statistics."

    @staticmethod
    def get_disk_usage() -> str:
        """Queries disk space usage on the primary drive."""
        try:
            # Query the root directory of the primary Windows drive
            usage = psutil.disk_usage('C:\\')
            free_gb = round(usage.free / (1024**3), 1)
            total_gb = round(usage.total / (1024**3), 1)
            return f"Primary C drive usage is at {usage.percent} percent. There are {free_gb} gigabytes free out of {total_gb} gigabytes total space."
        except Exception as e:
            logger.log_error(f"Error querying disk space: {e}")
            return "Unable to retrieve storage statistics."

    @staticmethod
    def get_temperature_status() -> str:
        """Attempts to retrieve hardware temperature status."""
        try:
            if not hasattr(psutil, "sensors_temperatures"):
                return "Hardware temperature sensors are unsupported on this platform."
            
            temps = psutil.sensors_temperatures()
            if not temps:
                return "No temperature sensors were detected on this Windows machine. This is common if running in a virtual machine or on specific desktop hardware."
            
            # Try to summarize temperatures
            summary = []
            for name, entries in temps.items():
                if entries:
                    avg_temp = sum(e.current for e in entries) / len(entries)
                    summary.append(f"{name}: {round(avg_temp, 1)} degrees Celsius")
            
            return "Current system temperatures: " + ", ".join(summary)
        except Exception as e:
            logger.log_error(f"Error querying temperature: {e}")
            return "Unable to retrieve system temperature status."

    @classmethod
    def execute_system_info_command(cls, command_text: str) -> tuple[bool, str]:
        """Routes system queries to the correct diagnostics routine."""
        cmd_clean = command_text.strip().lower()
        
        if "battery" in cmd_clean:
            return True, cls.get_battery_status()
        elif "system information" in cmd_clean or "system info" in cmd_clean or "pc specs" in cmd_clean:
            return True, cls.get_system_info()
        elif "cpu" in cmd_clean:
            return True, cls.get_cpu_usage()
        elif "ram" in cmd_clean or "memory" in cmd_clean:
            return True, cls.get_ram_usage()
        elif "disk" in cmd_clean or "storage" in cmd_clean or "space" in cmd_clean:
            return True, cls.get_disk_usage()
        elif "temperature" in cmd_clean or "temp" in cmd_clean:
            return True, cls.get_temperature_status()
            
        return False, "Could not determine system parameter to check. You can ask for: battery status, CPU usage, RAM usage, disk space, or system information."
