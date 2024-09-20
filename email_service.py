import logging
import httpx
from models import Subscriber, Unsubscriber
from config import RESEND_API_KEY, RESEND_API_URL, EMAIL_CONFIG

logger = logging.getLogger(__name__)

async def send_welcome_email(subscriber: Subscriber):
    logger.info(f"Starting to send welcome email to: {subscriber.email}")
    try:
        with open("welcome_email_template.html", "r") as f:
            template = f.read()

        expectations_html = "".join([f"<li>{item.strip()}</li>" for item in EMAIL_CONFIG["expectations"]])

        html_content = template.format(
            email_subject=EMAIL_CONFIG["email_subject"],
            header_color=EMAIL_CONFIG["header_color"],
            logo_url=EMAIL_CONFIG["logo_url"],
            main_heading=EMAIL_CONFIG["main_heading"].format(first_name=subscriber.firstName),
            first_name=subscriber.firstName,
            last_name=subscriber.lastName,
            welcome_message=EMAIL_CONFIG["welcome_message"],
            expectations=expectations_html,
            closing_message=EMAIL_CONFIG["closing_message"],
            team_name=EMAIL_CONFIG["team_name"]
        )

        await send_email(subscriber.email, EMAIL_CONFIG["email_subject"], html_content)
        logger.info(f"Welcome email sent successfully to: {subscriber.email}")
    except Exception as e:
        logger.error(f"An unexpected error occurred while sending welcome email: {str(e)}", exc_info=True)

async def send_unsubscribe_confirmation_email(unsubscriber: Unsubscriber):
    logger.info(f"Starting to send unsubscribe confirmation email to: {unsubscriber.email}")
    try:
        html_content = f"""
        <h1>Unsubscribe Confirmation</h1>
        <p>You have been successfully unsubscribed from our newsletter. We're sorry to see you go!</p>
        """
        await send_email(unsubscriber.email, "Unsubscribe Confirmation", html_content)
        logger.info(f"Unsubscribe confirmation email sent successfully to: {unsubscriber.email}")
    except Exception as e:
        logger.error(f"An unexpected error occurred while sending unsubscribe confirmation email: {str(e)}", exc_info=True)

async def send_email(to_email: str, subject: str, content: str):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{RESEND_API_URL}/emails",
            json={
                "from": "onboarding@resend.dev",
                "to": to_email,
                "subject": subject,
                "html": content
            },
            headers={"Authorization": f"Bearer {RESEND_API_KEY}"}
        )
        response.raise_for_status()
        return response.json()
