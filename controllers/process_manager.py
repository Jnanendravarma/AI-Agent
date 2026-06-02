import psutil
from utils.logger import logger

class ProcessManager:
    @staticmethod
    def find_processes_by_name(process_name: str):
        """
        Finds all active processes matching the specified process name.
        """
        matching_processes = []
        try:
            for proc in psutil.process_iter(['pid', 'name']):
                if proc.info['name'] and proc.info['name'].lower() == process_name.lower():
                    matching_processes.append(proc)
        except Exception as e:
            logger.log_error(f"Error finding processes for {process_name}: {e}")
        return matching_processes

    @staticmethod
    def kill_process_by_name(process_name: str) -> bool:
        """
        Terminates all instances of a process with the specified name.
        """
        targets = ProcessManager.find_processes_by_name(process_name)
        if not targets:
            logger.log_error(f"No active processes found matching: {process_name}")
            return False

        success = False
        for proc in targets:
            try:
                proc.terminate()  # Try graceful termination first
                # Wait briefly or kill it
                try:
                    proc.wait(timeout=1)
                except psutil.TimeoutExpired:
                    proc.kill()  # Force termination if timeout expires
                success = True
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess) as e:
                logger.log_error(f"Failed to terminate process pid={proc.pid} ({process_name}): {e}")
                
        return success
