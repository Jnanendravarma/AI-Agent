import os
from utils.logger import logger
from ai.gemini_client import GeminiClient

PDF_READER_AVAILABLE = False
try:
    from pypdf import PdfReader
    PDF_READER_AVAILABLE = True
except ImportError:
    logger.log_error("pypdf package not installed. PDF features will not work.")

class PDFService:
    @staticmethod
    def get_most_recent_pdf() -> str:
        """Looks inside Desktop, Documents, and Downloads for the most recently modified PDF file."""
        search_paths = [
            os.path.expanduser("~/Downloads"),
            os.path.expanduser("~/Documents"),
            os.path.expanduser("~/Desktop")
        ]
        
        most_recent_file = None
        most_recent_time = 0.0
        
        for base_path in search_paths:
            if not os.path.exists(base_path):
                continue
            try:
                for root, _, files in os.walk(base_path):
                    # Limit walk depth to 2
                    depth = root[len(base_path):].count(os.sep)
                    if depth > 2:
                        continue
                    for f in files:
                        if f.lower().endswith(".pdf"):
                            full_path = os.path.join(root, f)
                            try:
                                mtime = os.path.getmtime(full_path)
                                if mtime > most_recent_time:
                                    most_recent_time = mtime
                                    most_recent_file = full_path
                            except Exception:
                                pass
            except Exception as e:
                logger.log_error(f"Error searching directory for PDFs: {e}")
                
        return most_recent_file

    @staticmethod
    def extract_text_from_pdf(filepath: str, max_pages=15) -> str:
        """Extracts text from PDF file (reads up to max_pages to protect token bounds)."""
        if not PDF_READER_AVAILABLE:
            return "Error: pypdf library is not installed."
        if not os.path.exists(filepath):
            return f"Error: File '{filepath}' does not exist."

        try:
            reader = PdfReader(filepath)
            text = ""
            pages_to_read = min(len(reader.pages), max_pages)
            for i in range(pages_to_read):
                page_text = reader.pages[i].extract_text()
                if page_text:
                    text += f"\n--- PAGE {i+1} ---\n{page_text}"
            return text
        except Exception as e:
            logger.log_error(f"Failed to parse PDF: {e}")
            return f"Error reading PDF file: {str(e)}"

    @classmethod
    def execute_pdf_action(cls, gemini_client: GeminiClient, command_text: str) -> tuple[bool, str]:
        """
        Executes instructions over the local PDF: summarization, notes, skill extraction, explaining, or answering questions.
        If no path is specified, searches for the most recent PDF automatically.
        """
        if not PDF_READER_AVAILABLE:
            return False, "PDF processing is disabled because pypdf is not installed."

        # Scan command text to see if user specified an absolute or relative file path
        pdf_path = None
        words = command_text.split()
        for word in words:
            cleaned_word = word.strip('"\'')
            if cleaned_word.lower().endswith(".pdf") and os.path.exists(cleaned_word):
                pdf_path = cleaned_word
                break

        # Fallback to scanning Downloads/Documents/Desktop for the most recent PDF
        if not pdf_path:
            pdf_path = cls.get_most_recent_pdf()

        if not pdf_path:
            return False, "I could not find any PDF document in your Desktop, Documents, or Downloads folders to analyze."

        filename = os.path.basename(pdf_path)
        logger.log_command(command_text, "Success", f"Processing PDF: '{filename}' at path: '{pdf_path}'")

        text_content = cls.extract_text_from_pdf(pdf_path)
        if text_content.startswith("Error:"):
            return False, text_content

        prompt = f"""
You are an expert PDF Analyzer.
Below is the text content extracted from the document: "{filename}" (up to 15 pages).

--- BEGIN DOCUMENT CONTENT ---
{text_content}
--- END DOCUMENT CONTENT ---

The user asked the following question/command regarding this document:
"{command_text}"

Perform the task (e.g. summarize, extract skills, explain content, generate notes, or answer questions).
Keep the response concise, clear, and structured.
"""
        response, err = gemini_client.generate_content(prompt, model_name="gemini-2.5-flash")
        if err:
            return False, f"Failed to analyze PDF content: {err}"

        return True, f"Analysis of document '{filename}':\n\n{response}"
