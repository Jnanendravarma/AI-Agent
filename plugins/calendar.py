from plugins.base_plugin import BasePlugin
from services.calendar_service import CalendarService

class CalendarPlugin(BasePlugin):
    def __init__(self, executor):
        super().__init__(executor)
        self.cal_service = CalendarService()

    def get_keywords(self) -> list[str]:
        return ["meeting", "schedule", "calendar", "appointment", "agenda"]

    def execute(self, command: str) -> tuple[bool, str]:
        cmd_lower = command.lower().strip()
        
        # Route to CalendarService
        if "show" in cmd_lower or "list" in cmd_lower or "agenda" in cmd_lower:
            return self.cal_service.list_events(command)
        elif "create" in cmd_lower or "add" in cmd_lower or "schedule" in cmd_lower:
            return self.cal_service.add_event(command)
        else:
            return self.cal_service.list_events("show today's schedule")
        
        return False, "Command not recognized by Calendar plugin"
