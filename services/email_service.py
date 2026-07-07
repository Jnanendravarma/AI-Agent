import os
from utils.logger import logger

class EmailService:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(EmailService, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self.pending_email = None
        self._initialized = True

    def compose_email(self, to_addr: str, subject: str, body: str, attachment: str = None) -> tuple[bool, str]:
        """
        Drafts an email and saves it to the pending slot.
        Requests user confirmation before actual dispatch.
        """
        self.pending_email = {
            "to": to_addr,
            "subject": subject,
            "body": body,
            "attachment": attachment
        }
        
        attach_msg = f" with attachment '{os.path.basename(attachment)}'" if attachment else ""
        return True, f"I have composed the email to {to_addr} (Subject: '{subject}'){attach_msg}. Are you sure you want to send it?"

    def send_pending_email(self) -> tuple[bool, str]:
        """Sends the pending email. Simulates SMTP operations cleanly."""
        if not self.pending_email:
            return False, "No email draft is pending."

        try:
            to = self.pending_email["to"]
            subj = self.pending_email["subject"]
            
            # Simple simulation logs
            logger.log_info(f"Sending email: To: {to} | Subject: {subj}")
            self.pending_email = None
            return True, f"Email sent successfully to {to}."
        except Exception as e:
            logger.log_error(f"Failed to send email: {e}")
            self.pending_email = None
            return False, f"Failed to send email: {e}"

    def cancel_pending_email(self) -> str:
        self.pending_email = None
        return "Email draft discarded."

    def read_latest_emails(self) -> tuple[bool, str]:
        """Returns mock inbox entries."""
        mock_inbox = [
            {"from": "HR Team", "subject": "Interview Schedule", "body": "Please confirm your availability for tomorrow at 2 PM."},
            {"from": "GitHub", "subject": "[GitHub] Security Alert", "body": "We detected a new security vulnerability on your repository."},
            {"from": "Manager", "subject": "Project EventHub Status Update", "body": "Please send the status report by end of day today."}
        ]
        
        lines = []
        for i, email in enumerate(mock_inbox, 1):
            lines.append(f"{i}. From {email['from']}: '{email['subject']}'")
        return True, "Here are your latest emails: " + "; and ".join(lines)

    def generate_professional_reply(self, email_index: int) -> tuple[bool, str]:
        """Generates a professional reply template using Gemini."""
        mock_inbox = [
            {"from": "HR Team", "subject": "Interview Schedule", "body": "Please confirm your availability for tomorrow at 2 PM."},
            {"from": "GitHub", "subject": "[GitHub] Security Alert", "body": "We detected a new security vulnerability on your repository."},
            {"from": "Manager", "subject": "Project EventHub Status Update", "body": "Please send the status report by end of day today."}
        ]
        
        idx = email_index - 1
        if not (0 <= idx < len(mock_inbox)):
            return False, "Invalid email index selected."
            
        target = mock_inbox[idx]
        
        # Verify online state
        from engine.command_executor import CommandExecutor
        executor = CommandExecutor()
        is_online = getattr(executor, "online", True)
        
        if is_online and hasattr(executor, "gemini_client"):
            prompt = f"Draft a professional reply to this email:\nFrom: {target['from']}\nSubject: {target['subject']}\nBody: {target['body']}\nKeep the draft very concise and professional."
            res, err = executor.gemini_client.generate_content(prompt)
            if res and not err:
                return True, f"Here is a drafted reply:\n\n{res}"

        # Offline fallback reply template
        fallback_reply = f"Subject: Re: {target['subject']}\n\nHi {target['from']},\n\nThank you for the message. I have received your email and will follow up shortly.\n\nBest regards,\nJnanendra"
        return True, f"Here is the template reply (Offline):\n\n{fallback_reply}"
