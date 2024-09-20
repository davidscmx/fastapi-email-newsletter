import logging
import os
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from models import Subscriber, Unsubscriber
from config import RESEND_API_KEY, RESEND_AUDIENCE_ID
from email_service import send_email
from subscription_service import subscribe, unsubscribe, get_subscribers
from utils import limiter, setup_rate_limiting
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
import secrets

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI()
setup_rate_limiting(app)

app.mount("/static", StaticFiles(directory="."), name="static")

scheduler = AsyncIOScheduler()
security = HTTPBasic()

# Load admin credentials from environment variables
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "change_this_password")

@app.on_event("startup")
async def startup_event():
    scheduler.start()
    scheduler.add_job(send_scheduled_newsletter, trigger=CronTrigger(day_of_week="mon", hour=9, minute=0))

@app.on_event("shutdown")
async def shutdown_event():
    scheduler.shutdown()

@app.get("/", response_class=HTMLResponse)
async def root():
    logger.info("Serving root endpoint")
    with open("index.html", "r") as f:
        return f.read()

@app.post("/subscribe")
@limiter.limit("3/minute")
async def subscribe_route(request: Request, subscriber: Subscriber):
    return await subscribe(subscriber)

@app.post("/unsubscribe")
@limiter.limit("3/minute")
async def unsubscribe_route(request: Request, unsubscriber: Unsubscriber):
    return await unsubscribe(unsubscriber)

def get_current_username(credentials: HTTPBasicCredentials = Depends(security)):
    logger.info(f"Attempting authentication for user: {credentials.username}")
    logger.info(f"Expected username: {ADMIN_USERNAME}")
    correct_username = secrets.compare_digest(credentials.username, ADMIN_USERNAME)
    correct_password = secrets.compare_digest(credentials.password, ADMIN_PASSWORD)
    
    if not (correct_username and correct_password):
        logger.warning(f"Authentication failed for user '{credentials.username}'")
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    
    logger.info(f"Authentication successful for user '{credentials.username}'")
    return credentials.username

@app.get("/admin/stats")
async def admin_stats(username: str = Depends(get_current_username)):
    logger.info(f"Fetching admin stats for user '{username}'")
    subscribers = await get_subscribers()
    total_subscribers = len(subscribers)
    active_subscribers = sum(1 for sub in subscribers if not sub.get('unsubscribed', False))
    return JSONResponse({
        "total_subscribers": total_subscribers,
        "active_subscribers": active_subscribers,
        "inactive_subscribers": total_subscribers - active_subscribers
    })

async def send_scheduled_newsletter():
    logger.info("Sending scheduled newsletter")
    subscribers = await get_subscribers()
    active_subscribers = [sub for sub in subscribers if not sub.get('unsubscribed', False)]
    
    content = f"""
    <h1>Your Weekly Newsletter</h1>
    <p>Here's your weekly update from us!</p>
    <p>Date: {datetime.now().strftime('%Y-%m-%d')}</p>
    <p>This week's highlights:</p>
    <ul>
        <li>New feature: Customizable email templates</li>
        <li>Upcoming event: Tech Talk on AI in Newsletter Management</li>
        <li>Tips: How to increase your newsletter engagement</li>
    </ul>
    <p>Stay tuned for more exciting updates!</p>
    """
    
    for subscriber in active_subscribers:
        await send_email(subscriber['email'], "Your Weekly Newsletter", content)
    
    logger.info(f"Scheduled newsletter sent to {len(active_subscribers)} active subscribers")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
