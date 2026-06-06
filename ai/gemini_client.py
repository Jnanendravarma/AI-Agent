import os
import time
from utils.logger import logger
from dotenv import load_dotenv

# Try importing google.generativeai
GEMINI_AVAILABLE = False
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    logger.log_error("google-generativeai package not installed.")

# Load environments
load_dotenv()

class GeminiClient:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.client_initialized = False
        
        if not GEMINI_AVAILABLE:
            logger.log_error("Gemini SDK not available. Gemini client cannot function.")
            return

        if self.api_key:
            try:
                genai.configure(api_key=self.api_key)
                self.client_initialized = True
                logger.log_command("Gemini Client", "Success", "Configured API key successfully.")
            except Exception as e:
                logger.log_error(f"Failed to configure Gemini API: {e}")
        else:
            logger.log_error("GEMINI_API_KEY environment variable is missing in .env.")

    def generate_content(self, prompt: str, image=None, model_name="gemini-2.5-flash", retries=3, backoff_factor=2) -> tuple[str, str]:
        """
        Queries Gemini API for text or multimodal content generation.
        Includes a retry mechanism with exponential backoff.
        Returns a tuple of (response_text, error_message).
        """
        if not self.client_initialized:
            return None, "Gemini client is not configured or initialized. Please check GEMINI_API_KEY."

        try:
            model = genai.GenerativeModel(model_name)
        except Exception as e:
            return None, f"Failed to instantiate model '{model_name}': {e}"

        contents = []
        if image:
            contents.append(image)
        contents.append(prompt)

        for attempt in range(retries):
            try:
                response = model.generate_content(contents)
                if response and response.text:
                    return response.text.strip(), None
                else:
                    return "", "Empty response returned from Gemini."
            except Exception as e:
                err_msg = str(e)
                logger.log_error(f"Gemini API call failed (attempt {attempt + 1}/{retries}): {err_msg}")
                if attempt < retries - 1:
                    time.sleep(backoff_factor ** attempt)
                else:
                    return None, f"Gemini API Error after {retries} retries: {err_msg}"
        
        return None, "Failed to get response from Gemini."
