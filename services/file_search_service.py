import os
import fnmatch
from utils.logger import logger

class FileSearchService:
    # Selected directories to scan by default
    DEFAULT_SEARCH_PATHS = [
        os.path.expanduser("~/Desktop"),
        os.path.expanduser("~/Documents"),
        os.path.expanduser("~/Downloads")
    ]

    @classmethod
    def search_files(cls, query: str, search_paths=None) -> list[str]:
        """
        Recursively searches the specified paths for files that match the query.
        Returns a list of matching absolute file paths.
        """
        if not search_paths:
            search_paths = cls.DEFAULT_SEARCH_PATHS

        query = query.strip().lower()
        matches = []

        for base_path in search_paths:
            if not os.path.exists(base_path):
                continue
                
            # Limit depth of recursive walk to prevent performance locking on huge user directories
            for root, dirs, files in os.walk(base_path):
                # Calculate current depth
                depth = root[len(base_path):].count(os.sep)
                if depth > 3:  # Don't go deeper than 3 subfolders
                    # Mutate dirs in place to prevent os.walk from recursing further
                    dirs.clear()
                    continue

                for filename in files:
                    if query in filename.lower():
                        full_path = os.path.join(root, filename)
                        matches.append(full_path)
                        # Cap at 5 total matches to keep spoken responses concise
                        if len(matches) >= 5:
                            return matches
                            
        return matches

    @classmethod
    def execute_file_search(cls, command_text: str) -> tuple[bool, str]:
        """
        Parses and runs file search command.
        Commands:
        - "find resume.pdf"
        - "search file campuscare"
        - "find and open project report"
        """
        cmd_clean = command_text.strip().lower()
        
        # Parse out search query
        # Support prefixes: "find and open", "find", "search file", "search for file", "search"
        prefixes = ["find and open", "find", "search file", "search for file", "search"]
        query = ""
        open_requested = "open" in cmd_clean
        
        for prefix in prefixes:
            if cmd_clean.startswith(prefix):
                query = cmd_clean[len(prefix):].strip()
                break
                
        if not query:
            query = cmd_clean
            
        # Clean query further (remove helper words)
        query = query.replace("file", "").strip()
        
        if not query:
            return False, "What filename or search query should I look for?"

        matches = cls.search_files(query)
        
        if not matches:
            return False, f"I searched your Desktop, Documents, and Downloads folders but couldn't find any files matching '{query}'."

        # If we found matches
        if len(matches) == 1:
            matched_file = matches[0]
            filename = os.path.basename(matched_file)
            
            if open_requested:
                try:
                    os.startfile(matched_file)
                    return True, f"Found and opened {filename} at {matched_file}"
                except Exception as e:
                    logger.log_error(f"Failed to open file {matched_file}: {e}")
                    return True, f"Found {filename} at {matched_file}, but could not open it automatically."
            else:
                # Store the last searched file path in a class attribute so user can say "open it" as follow-up
                cls.last_found_file = matched_file
                return True, f"I found one match: {filename} located at {matched_file}. You can say open file if you'd like to open it."
        else:
            cls.last_found_file = matches[0]  # Store first one
            file_list = ", ".join(os.path.basename(m) for m in matches)
            return True, f"I found {len(matches)} matches: {file_list}. The first match is located at {matches[0]}."

    # Cache last found file for "open it" follow up commands
    last_found_file = None

    @classmethod
    def open_last_found_file(cls) -> tuple[bool, str]:
        """Opens the last successfully searched file."""
        if not cls.last_found_file or not os.path.exists(cls.last_found_file):
            return False, "No recently found file to open."
            
        try:
            os.startfile(cls.last_found_file)
            return True, f"Opening {os.path.basename(cls.last_found_file)}"
        except Exception as e:
            logger.log_error(f"Failed to open cached file: {e}")
            return False, "Could not open the file."
