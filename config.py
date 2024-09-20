import os
from dotenv import load_dotenv

load_dotenv()

RESEND_API_KEY = os.getenv("RESEND_API_KEY")
RESEND_AUDIENCE_ID = os.getenv("RESEND_AUDIENCE_ID")
RESEND_API_URL = "https://api.resend.com"

EMAIL_CONFIG = {
    "email_subject": os.getenv("EMAIL_SUBJECT", "Welcome to Our Awesome Newsletter!"),
    "header_color": os.getenv("EMAIL_HEADER_COLOR", "#007bff"),
    "logo_url": os.getenv("EMAIL_LOGO_URL", "https://example.com/logo.png"),
    "main_heading": os.getenv("EMAIL_MAIN_HEADING", "Welcome to Our Newsletter, {first_name}!"),
    "welcome_message": os.getenv("EMAIL_WELCOME_MESSAGE", "Thank you for subscribing to our newsletter. We're excited to have you on board!"),
    "expectations": os.getenv("EMAIL_EXPECTATIONS", "Weekly updates on industry trends,Exclusive content and offers,Tips and tricks to help you succeed").split(','),
    "closing_message": os.getenv("EMAIL_CLOSING_MESSAGE", "If you have any questions or feedback, feel free to reply to this email."),
    "team_name": os.getenv("EMAIL_TEAM_NAME", "The Newsletter Team")
}
