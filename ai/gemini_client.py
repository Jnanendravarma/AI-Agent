import os
import time
from utils.logger import logger
from dotenv import load_dotenv

# Try importing the new google-genai SDK
GEMINI_AVAILABLE = False
try:
    from google import genai
    from google.genai.errors import APIError
    GEMINI_AVAILABLE = True
except ImportError:
    logger.log_error("google-genai package not installed.")

# Load environment variables
load_dotenv()

class GeminiClient:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.client_initialized = False
        self.client = None
        self.default_model = "gemini-2.5-flash"  # Default fallback model
        
        if not GEMINI_AVAILABLE:
            logger.log_error("Gemini SDK (google-genai) not available. Gemini client cannot function.")
            return

        if self.api_key:
            try:
                self.client = genai.Client(api_key=self.api_key)
                self.client_initialized = True
                logger.log_command("Gemini Client", "Success", "Configured API key successfully.")
                self.check_model_availability()
            except Exception as e:
                logger.log_error(f"Failed to configure Gemini API client: {e}")
        else:
            logger.log_error("GEMINI_API_KEY environment variable is missing in .env.")

    def check_model_availability(self):
        """Scans and selects the best available model, verifying connectivity."""
        if not self.client_initialized or not self.client:
            return

        candidate_models = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"]
        
        # 1. Attempt to list models via API
        try:
            available_models = [m.name for m in self.client.models.list()]
            for candidate in candidate_models:
                # API lists models as 'models/gemini-X.Y-flash' or similar
                if candidate in available_models or f"models/{candidate}" in available_models:
                    self.default_model = candidate
                    logger.log_command("Gemini Model Check", "Success", f"Automatically selected available model: {candidate}")
                    return
        except Exception as e:
            logger.log_error(f"Could not list models: {e}. Testing candidate models individually.")

        # 2. Fallback: lightweight connectivity checks on candidate models
        for candidate in candidate_models:
            try:
                # Tiny text generation test
                self.client.models.generate_content(
                    model=candidate,
                    contents="ping"
                )
                self.default_model = candidate
                logger.log_command("Gemini Model Check", "Success", f"Verified model availability: {candidate}")
                return
            except Exception as e:
                logger.log_error(f"Model {candidate} test failed: {e}")

        logger.log_error(f"All model availability tests failed. Falling back to default model: {self.default_model}")

    def generate_content(self, prompt: str, image=None, model_name=None, retries=3, backoff_factor=2) -> tuple[str, str]:
        """
        Queries Gemini API using the new Client.
        Includes a customized error check to abort retries on 429 quota exhaustion.
        Returns a tuple of (response_text, error_message).
        """
        if not self.client_initialized or not self.client:
            return None, "Gemini client is not configured or initialized. Please check GEMINI_API_KEY."

        # Use class default model if model_name is not provided or set to default
        if not model_name or model_name == "gemini-2.5-flash":
            model_name = self.default_model

        # Build contents list (multimodal supports PIL Images directly)
        contents = []
        if image:
            contents.append(image)
        contents.append(prompt)

        for attempt in range(retries):
            try:
                response = self.client.models.generate_content(
                    model=model_name,
                    contents=contents
                )
                if response and response.text:
                    return response.text.strip(), None
                else:
                    return "", "Empty response returned from Gemini."

            except APIError as e:
                err_msg = str(e)
                # Check for 429 Quota Exceeded (Resource Exhausted)
                is_429 = getattr(e, 'code', None) == 429 or "429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg
                is_auth_error = getattr(e, 'code', None) in [401, 403] or "API_KEY_INVALID" in err_msg or "invalid" in err_msg.lower()
                
                if is_429:
                    logger.log_error(f"Gemini API Quota Exceeded (429). Immediately stopping retries.")
                    return None, "AI service is busy. Please try again after a minute."
                
                if is_auth_error:
                    logger.log_error(f"Gemini API authentication failed. Stopping retries.")
                    return None, "Gemini API key is invalid or unauthorized."

                if getattr(e, 'code', None) == 400:
                    logger.log_error(f"Gemini API Bad Request. Stopping retries: {err_msg}")
                    return None, f"Gemini API Bad Request: {err_msg}"

                logger.log_error(f"Gemini API error (attempt {attempt + 1}/{retries}): {err_msg}")
                if attempt < retries - 1:
                    time.sleep(backoff_factor ** attempt)
                else:
                    return None, "AI service is temporarily unavailable. Please try again later."

            except Exception as e:
                # Catch general network issues/timeouts
                err_msg = str(e)
                logger.log_error(f"Connection failure (attempt {attempt + 1}/{retries}): {err_msg}")
                if attempt < retries - 1:
                    time.sleep(backoff_factor ** attempt)
                else:
                    return None, "AI service is temporarily unavailable. Please try again later."

        return None, "Failed to get response from Gemini."

