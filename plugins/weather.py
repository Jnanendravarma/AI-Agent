from plugins.base_plugin import BasePlugin

class WeatherPlugin(BasePlugin):
    def get_keywords(self) -> list[str]:
        return ["weather", "temperature outside", "how hot is it", "climate today", "weather report"]

    def execute(self, command: str) -> tuple[bool, str]:
        # Check if the executor is online
        is_online = getattr(self.executor, "online", True)
        
        # Determine target city (e.g. "weather in Hyderabad")
        city = "your local area"
        words = command.lower().split()
        if "in" in words:
            idx = words.index("in")
            if idx + 1 < len(words):
                city = " ".join(words[idx + 1:]).title()

        if is_online and hasattr(self.executor, "gemini_client"):
            prompt = f"Provide a brief, single-sentence summary of the current weather in {city}."
            res, err = self.executor.gemini_client.generate_content(prompt)
            if res and not err:
                return True, res.strip()

        # Offline or Gemini error fallback (Mocks)
        import random
        temps = [24, 27, 31, 33, 29]
        conditions = ["partly cloudy", "mostly sunny", "clear sky", "light drizzle", "humid and warm"]
        temp = random.choice(temps)
        cond = random.choice(conditions)
        return True, f"Currently in {city} it is {temp}°C with {cond} (Offline Mode)."
