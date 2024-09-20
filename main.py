import os
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, EmailStr
from dotenv import load_dotenv
import httpx
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# Load environment variables
load_dotenv()

limiter = Limiter(key_func=get_remote_address)
app = FastAPI()
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

class Subscriber(BaseModel):
    email: EmailStr
    firstName: str
    lastName: str

class Unsubscriber(BaseModel):
    email: EmailStr

# Resend API configuration
RESEND_API_KEY = os.getenv("RESEND_API_KEY")
RESEND_AUDIENCE_ID = os.getenv("RESEND_AUDIENCE_ID")
RESEND_API_URL = "https://api.resend.com"

@app.get("/")
async def root():
    return {"message": "Welcome to the Newsletter Subscription Service"}

@app.post("/subscribe")
@limiter.limit("3/minute")
async def subscribe(request: Request, subscriber: Subscriber):
    try:
        # Add subscriber to Resend audience
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{RESEND_API_URL}/audiences/{RESEND_AUDIENCE_ID}/contacts",
                json={
                    "email": subscriber.email,
                    "first_name": subscriber.firstName,
                    "last_name": subscriber.lastName
                },
                headers={"Authorization": f"Bearer {RESEND_API_KEY}"}
            )
            response.raise_for_status()

        # Send welcome email
        await send_welcome_email(subscriber)

        return {"message": "Subscription successful! Welcome email sent."}
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail="Failed to add subscriber to Resend audience")
    except Exception as e:
        raise HTTPException(status_code=500, detail="An error occurred during subscription")

@app.post("/unsubscribe")
@limiter.limit("3/minute")
async def unsubscribe(request: Request, unsubscriber: Unsubscriber):
    try:
        # Update subscriber status in Resend audience
        async with httpx.AsyncClient() as client:
            response = await client.patch(
                f"{RESEND_API_URL}/audiences/{RESEND_AUDIENCE_ID}/contacts/{unsubscriber.email}",
                json={"unsubscribed": True},
                headers={"Authorization": f"Bearer {RESEND_API_KEY}"}
            )
            response.raise_for_status()

        # Send unsubscribe confirmation email
        await send_unsubscribe_confirmation_email(unsubscriber)

        return {"message": "Unsubscribe successful! Confirmation email sent."}
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise HTTPException(status_code=404, detail="Email not found in the subscriber list")
        raise HTTPException(status_code=e.response.status_code, detail="Failed to update subscriber status in Resend audience")
    except Exception as e:
        raise HTTPException(status_code=500, detail="An error occurred during unsubscription")

async def send_welcome_email(subscriber: Subscriber):
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{RESEND_API_URL}/emails",
                json={
                    "from": "onboarding@resend.dev",
                    "to": subscriber.email,
                    "subject": "Welcome to Our Newsletter!",
                    "html": f"""
                    <h1>Welcome to Our Newsletter, {subscriber.firstName}!</h1>
                    <p>Thank you for subscribing, {subscriber.firstName} {subscriber.lastName}. We're excited to have you on board!</p>
                    """
                },
                headers={"Authorization": f"Bearer {RESEND_API_KEY}"}
            )
            response.raise_for_status()
    except httpx.HTTPStatusError as e:
        print(f"Failed to send welcome email: {e}")

async def send_unsubscribe_confirmation_email(unsubscriber: Unsubscriber):
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
    except httpx.HTTPStatusError as e:
        print(f"Failed to send unsubscribe confirmation email: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
