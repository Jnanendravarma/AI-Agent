import webbrowser
import urllib.parse
import re
from utils.logger import logger

class SearchService:
    @staticmethod
    def execute_search(query_text: str) -> tuple[bool, str]:
        """
        Parses search commands and opens corresponding search pages in the browser.
        Supports:
        - YouTube search: e.g. "search youtube python tutorial"
        - Stack Overflow search: e.g. "open stack overflow react state management"
        - GitHub search: e.g. "search github react hooks"
        - Google search: e.g. "search python decorators", "google AI agents"
        """
        try:
            query_clean = query_text.strip().lower()
            
            # 1. YouTube Search
            if "youtube" in query_clean:
                # Remove trigger keywords
                pattern = r"(?:search\s+on\s+youtube|search\s+youtube|youtube\s+search|youtube|open\s+youtube\s+and\s+search)\s*(.*)"
                match = re.search(pattern, query_clean)
                query = match.group(1).strip() if match else query_clean
                if not query:
                    webbrowser.open("https://www.youtube.com")
                    return True, "Opening YouTube"
                
                url = f"https://www.youtube.com/results?search_query={urllib.parse.quote_plus(query)}"
                webbrowser.open(url)
                return True, f"Searching YouTube for {query}"
            
            # 2. Stack Overflow Search
            elif "stack overflow" in query_clean or "stackoverflow" in query_clean:
                pattern = r"(?:open\s+stack\s+overflow|search\s+stack\s+overflow|stack\s+overflow|stackoverflow)\s*(.*)"
                match = re.search(pattern, query_clean)
                query = match.group(1).strip() if match else query_clean
                if not query:
                    webbrowser.open("https://stackoverflow.com")
                    return True, "Opening Stack Overflow"
                
                url = f"https://stackoverflow.com/search?q={urllib.parse.quote_plus(query)}"
                webbrowser.open(url)
                return True, f"Searching Stack Overflow for {query}"
                
            # 3. GitHub Search
            elif "github" in query_clean:
                pattern = r"(?:search\s+github(?:\s+repository)?|github\s+search|github)\s*(.*)"
                match = re.search(pattern, query_clean)
                query = match.group(1).strip() if match else query_clean
                if not query:
                    webbrowser.open("https://github.com")
                    return True, "Opening GitHub"
                
                url = f"https://github.com/search?q={urllib.parse.quote_plus(query)}"
                webbrowser.open(url)
                return True, f"Searching GitHub for {query}"
                
            # 4. Google Search (Default)
            else:
                pattern = r"(?:search\s+for|search\s+google|search|google|find)\s*(.*)"
                match = re.search(pattern, query_clean)
                query = match.group(1).strip() if match else query_clean
                if not query:
                    return False, "What would you like me to search for?"
                
                url = f"https://www.google.com/search?q={urllib.parse.quote_plus(query)}"
                webbrowser.open(url)
                return True, f"Searching Google for {query}"
                
        except Exception as e:
            logger.log_error(f"Search automation failed: {e}")
            return False, f"Failed to perform search: {str(e)}"
