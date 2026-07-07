class BasePlugin:
    def __init__(self, executor):
        self.executor = executor

    def get_keywords(self) -> list[str]:
        """Returns a list of trigger phrases or keywords for this plugin."""
        return []

    def execute(self, command: str) -> tuple[bool, str]:
        """
        Executes the matching command.
        Returns:
          - success (bool)
          - response_message (str)
        """
        return False, "Plugin not implemented"
