import os
import logging
from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, EmailStr
from dotenv import load_dotenv
import httpx
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

limiter = Limiter(key_func=get_remote_address)
app = FastAPI()
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.mount("/static", StaticFiles(directory="."), name="static")

class Subscriber(BaseModel):
    email: EmailStr
    firstName: str
    lastName: str

class Unsubscriber(BaseModel):
    email: EmailStr

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

@app.get("/", response_class=HTMLResponse)
async def root():
    logger.info("Serving root endpoint")
    with open("index.html", "r") as f:
        return f.read()

@app.post("/subscribe")
@limiter.limit("3/minute")
async def subscribe(request: Request, subscriber: Subscriber):
    logger.info(f"Starting subscription process for email: {subscriber.email}")
    try:
        logger.info(f"Subscriber state before API call: {subscriber}")
        async with httpx.AsyncClient() as client:
            logger.info(f"Fetching contact information for email: {subscriber.email}")
            response = await client.get(
                f"{RESEND_API_URL}/audiences/{RESEND_AUDIENCE_ID}/contacts",
                params={"email": subscriber.email},
                headers={"Authorization": f"Bearer {RESEND_API_KEY}"}
            )
            response.raise_for_status()
            contacts = response.json().get('data', [])
            logger.info(f"Received contacts data: {contacts}")
            
            existing_contact = next((contact for contact in contacts if contact['email'] == subscriber.email), None)
            
            if existing_contact:
                logger.info(f"Updating existing subscriber: {subscriber.email}")
                response = await client.patch(
                    f"{RESEND_API_URL}/audiences/{RESEND_AUDIENCE_ID}/contacts/{existing_contact['id']}",
                    json={
                        "first_name": subscriber.firstName,
                        "last_name": subscriber.lastName,
                        "unsubscribed": False
                    },
                    headers={"Authorization": f"Bearer {RESEND_API_KEY}"}
                )
                response.raise_for_status()
                logger.info(f"API response for updating subscriber: {response.text}")
                logger.info(f"Successfully updated subscriber: {subscriber.email}")
                message = "Your subscription has been updated. Welcome back!"
            else:
                logger.info(f"Adding new subscriber: {subscriber.email}")
                response = await client.post(
                    f"{RESEND_API_URL}/audiences/{RESEND_AUDIENCE_ID}/contacts",
                    json={
                        "email": subscriber.email,
                        "first_name": subscriber.firstName,
                        "last_name": subscriber.lastName,
                        "unsubscribed": False
                    },
                    headers={"Authorization": f"Bearer {RESEND_API_KEY}"}
                )
                response.raise_for_status()
                logger.info(f"API response for adding new subscriber: {response.text}")
                logger.info(f"Successfully added new subscriber: {subscriber.email}")
                message = "Subscription successful! Welcome to our newsletter."

        logger.info(f"Subscriber state after API call: {subscriber}")

        await send_welcome_email(subscriber)

        logger.info(f"Subscription process completed successfully for email: {subscriber.email}")
        return {"message": message}
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error occurred during subscription process: {e.response.status_code} - {e.response.text}", exc_info=True)
        raise HTTPException(status_code=e.response.status_code, detail=f"Failed to process subscription: {e.response.text}")
    except Exception as e:
        logger.error(f"An unexpected error occurred during subscription: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="An unexpected error occurred during subscription")

@app.post("/unsubscribe")
@limiter.limit("3/minute")
async def unsubscribe(request: Request, unsubscriber: Unsubscriber):
    logger.info(f"Starting unsubscription process for email: {unsubscriber.email}")
    try:
        async with httpx.AsyncClient() as client:
            logger.info(f"Fetching contact information for email: {unsubscriber.email}")
            response = await client.get(
                f"{RESEND_API_URL}/audiences/{RESEND_AUDIENCE_ID}/contacts",
                params={"email": unsubscriber.email},
                headers={"Authorization": f"Bearer {RESEND_API_KEY}"}
            )
            response.raise_for_status()
            contacts_data = response.json().get('data', [])
            logger.info(f"Received contacts data: {contacts_data}")

            if not contacts_data:
                logger.warning(f"Email not found in subscriber list: {unsubscriber.email}")
                raise HTTPException(status_code=404, detail="Email not found in the subscriber list")

            contact = next((c for c in contacts_data if c['email'] == unsubscriber.email), None)
            if not contact:
                logger.warning(f"Email not found in subscriber list: {unsubscriber.email}")
                raise HTTPException(status_code=404, detail="Email not found in the subscriber list")

            logger.info(f"Contact state before unsubscribe: {contact}")

            logger.info(f"Updating unsubscribed status for contact ID: {contact['id']}")
            response = await client.patch(
                f"{RESEND_API_URL}/audiences/{RESEND_AUDIENCE_ID}/contacts/{contact['id']}",
                json={"unsubscribed": True},
                headers={"Authorization": f"Bearer {RESEND_API_KEY}"}
            )
            response.raise_for_status()
            logger.info(f"API response for updating unsubscribed status: {response.text}")
            logger.info("Successfully updated unsubscribed status")

            response = await client.get(
                f"{RESEND_API_URL}/audiences/{RESEND_AUDIENCE_ID}/contacts/{contact['id']}",
                headers={"Authorization": f"Bearer {RESEND_API_KEY}"}
            )
            response.raise_for_status()
            updated_contact = response.json()
            logger.info(f"Contact state after unsubscribe: {updated_contact}")

        await send_unsubscribe_confirmation_email(unsubscriber)

        logger.info(f"Unsubscription process completed successfully for email: {unsubscriber.email}")
        return {"message": "Unsubscribe successful! Confirmation email sent."}
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error occurred during unsubscription: {e.response.status_code} - {e.response.text}", exc_info=True)
        raise HTTPException(status_code=e.response.status_code, detail=f"Failed to update subscriber status: {e.response.text}")
    except Exception as e:
        logger.error(f"An unexpected error occurred during unsubscription: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred during unsubscription: {str(e)}")

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

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{RESEND_API_URL}/emails",
                json={
                    "from": "onboarding@resend.dev",
                    "to": subscriber.email,
                    "subject": EMAIL_CONFIG["email_subject"],
                    "html": html_content
                },
                headers={"Authorization": f"Bearer {RESEND_API_KEY}"}
            )
            response.raise_for_status()
            logger.info(f"API response for sending welcome email: {response.text}")
        logger.info(f"Welcome email sent successfully to: {subscriber.email}")
    except httpx.HTTPStatusError as e:
        logger.error(f"Failed to send welcome email: {e.response.text}", exc_info=True)
    except Exception as e:
        logger.error(f"An unexpected error occurred while sending welcome email: {str(e)}", exc_info=True)

async def send_unsubscribe_confirmation_email(unsubscriber: Unsubscriber):
    logger.info(f"Starting to send unsubscribe confirmation email to: {unsubscriber.email}")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{RESEND_API_URL}/emails",
                json={
                    "from": "onboarding@resend.dev",
                    "to": unsubscriber.email,
                    "subject": "Unsubscribe Confirmation",
                    "html": f"""
                    <h1>Unsubscribe Confirmation</h1>
                    <p>You have been successfully unsubscribed from our newsletter. We're sorry to see you go!</p>
                    """
                },
                headers={"Authorization": f"Bearer {RESEND_API_KEY}"}
            )
            response.raise_for_status()
            logger.info(f"API response for sending unsubscribe confirmation email: {response.text}")
        logger.info(f"Unsubscribe confirmation email sent successfully to: {unsubscriber.email}")
    except httpx.HTTPStatusError as e:
        logger.error(f"Failed to send unsubscribe confirmation email: {e.response.text}", exc_info=True)
    except Exception as e:
        logger.error(f"An unexpected error occurred while sending unsubscribe confirmation email: {str(e)}", exc_info=True)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)