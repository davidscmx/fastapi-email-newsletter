import logging
import httpx
from fastapi import HTTPException
from models import Subscriber, Unsubscriber
from config import RESEND_API_KEY, RESEND_AUDIENCE_ID, RESEND_API_URL
from email_service import send_welcome_email, send_unsubscribe_confirmation_email

logger = logging.getLogger(__name__)

async def subscribe(subscriber: Subscriber):
    logger.info(f"Starting subscription process for email: {subscriber.email}")
    try:
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
                        "unsubscribed": False,
                        "data": {"preferences": subscriber.preferences}
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
                        "unsubscribed": False,
                        "data": {"preferences": subscriber.preferences}
                    },
                    headers={"Authorization": f"Bearer {RESEND_API_KEY}"}
                )
                response.raise_for_status()
                logger.info(f"API response for adding new subscriber: {response.text}")
                logger.info(f"Successfully added new subscriber: {subscriber.email}")
                message = "Subscription successful! Welcome to our newsletter."

        await send_welcome_email(subscriber)

        logger.info(f"Subscription process completed successfully for email: {subscriber.email}")
        return {"message": message}
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error occurred during subscription process: {e.response.status_code} - {e.response.text}", exc_info=True)
        raise HTTPException(status_code=e.response.status_code, detail=f"Failed to process subscription: {e.response.text}")
    except Exception as e:
        logger.error(f"An unexpected error occurred during subscription: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="An unexpected error occurred during subscription")

async def unsubscribe(unsubscriber: Unsubscriber):
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

async def get_subscribers():
    logger.info("Fetching all subscribers")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{RESEND_API_URL}/audiences/{RESEND_AUDIENCE_ID}/contacts",
                headers={"Authorization": f"Bearer {RESEND_API_KEY}"}
            )
            response.raise_for_status()
            subscribers = response.json().get('data', [])
            logger.info(f"Successfully fetched {len(subscribers)} subscribers")
            return subscribers
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error occurred while fetching subscribers: {e.response.status_code} - {e.response.text}", exc_info=True)
        raise HTTPException(status_code=e.response.status_code, detail=f"Failed to fetch subscribers: {e.response.text}")
    except Exception as e:
        logger.error(f"An unexpected error occurred while fetching subscribers: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="An unexpected error occurred while fetching subscribers")

async def get_subscriber_preferences(email: str):
    logger.info(f"Fetching preferences for subscriber: {email}")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{RESEND_API_URL}/audiences/{RESEND_AUDIENCE_ID}/contacts",
                params={"email": email},
                headers={"Authorization": f"Bearer {RESEND_API_KEY}"}
            )
            response.raise_for_status()
            contacts = response.json().get('data', [])
            
            if not contacts:
                logger.warning(f"Subscriber not found: {email}")
                return None

            subscriber = contacts[0]
            preferences = subscriber.get('data', {}).get('preferences', [])
            logger.info(f"Successfully fetched preferences for {email}: {preferences}")
            return preferences
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error occurred while fetching subscriber preferences: {e.response.status_code} - {e.response.text}", exc_info=True)
        raise HTTPException(status_code=e.response.status_code, detail=f"Failed to fetch subscriber preferences: {e.response.text}")
    except Exception as e:
        logger.error(f"An unexpected error occurred while fetching subscriber preferences: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="An unexpected error occurred while fetching subscriber preferences")