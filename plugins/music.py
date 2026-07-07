import webbrowser
from plugins.base_plugin import BasePlugin
from controllers.app_controller import AppController

class MusicPlugin(BasePlugin):
    def get_keywords(self) -> list[str]:
        return ["play music", "play song", "play track", "spotify", "music player"]

    def execute(self, command: str) -> tuple[bool, str]:
        cmd_lower = command.lower().strip()
        
        # Check if they want to play a specific song
        song_target = ""
        for trigger in ["play song", "play track", "play music", "play"]:
            if trigger in cmd_lower:
                parts = cmd_lower.split(trigger)
                if len(parts) > 1:
                    song_target = parts[1].strip()
                    break
        
        if song_target and song_target not in ["music", "song", "track"]:
            # Clean up target
            song_clean = song_target.replace("on spotify", "").replace("on youtube", "").strip()
            # If user explicitly requested spotify
            if "spotify" in cmd_lower:
                AppController.open_spotify()
                return True, f"Launching Spotify to search for '{song_clean}'."
            else:
                # Fallback to opening YouTube search/play (very robust, no account required)
                search_query = song_clean.replace(" ", "+")
                url = f"https://www.youtube.com/results?search_query={search_query}"
                webbrowser.open(url)
                return True, f"Searching and playing '{song_clean}' on YouTube."

        # If they just said "open spotify" or "play music" generically
        success = AppController.open_spotify()
        if success:
            return True, "Opening Spotify"
        return False, "Failed to launch Spotify player."
