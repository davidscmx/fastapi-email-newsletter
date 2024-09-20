import logging
from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from models import Subscriber, Unsubscriber, ABTestConfig
from config import RESEND_API_KEY, RESEND_AUDIENCE_ID
from email_service import send_email
from subscription_service import subscribe, unsubscribe, get_subscribers, get_subscriber_preferences
from utils import limiter, setup_rate_limiting
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
from analytics import analytics
import random

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI()
setup_rate_limiting(app)

app.mount("/static", StaticFiles(directory="."), name="static")

scheduler = AsyncIOScheduler()

ab_test_config = ABTestConfig(subject_a="Your Weekly Newsletter", subject_b="This Week's Exciting Updates")

@app.on_event("startup")
async def startup_event():
    scheduler.start()
    scheduler.add_job(send_scheduled_newsletter, trigger=CronTrigger(day_of_week="mon", hour=9, minute=0))
    scheduler.add_job(analytics.update_analytics, trigger=CronTrigger(hour='*'))  # Update analytics every hour

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
    result = await subscribe(subscriber)
    await analytics.update_analytics()
    return result

@app.post("/unsubscribe")
@limiter.limit("3/minute")
async def unsubscribe_route(request: Request, unsubscriber: Unsubscriber):
    result = await unsubscribe(unsubscriber)
    await analytics.update_analytics()
    return result

@app.get("/analytics")
async def get_analytics():
    await analytics.update_analytics()
    return JSONResponse(analytics.get_analytics_report())

@app.get("/preferences/{email}")
async def get_preferences(email: str):
    preferences = await get_subscriber_preferences(email)
    if preferences is None:
        return JSONResponse({"error": "Subscriber not found"}, status_code=404)
    return JSONResponse({"preferences": preferences})

async def send_scheduled_newsletter():
    logger.info("Sending scheduled newsletter")
    subscribers = await get_subscribers()
    active_subscribers = [sub for sub in subscribers if not sub.get('unsubscribed', False)]
    
    for subscriber in active_subscribers:
        content = await generate_personalized_content(subscriber)
        subject = choose_ab_test_subject(subscriber['email'])
        await send_email(subscriber['email'], subject, content)
    
    logger.info(f"Scheduled newsletter sent to {len(active_subscribers)} active subscribers")
    await analytics.update_analytics()

async def generate_personalized_content(subscriber):
    first_name = subscriber.get('first_name', 'Valued Subscriber')
    preferences = subscriber.get('data', {}).get('preferences', [])
    
    content = f"""
    <h1>Your Weekly Newsletter</h1>
    <p>Hello {first_name},</p>
    <p>Here's your personalized weekly update based on your preferences:</p>
    """

    if "tech" in preferences:
        content += "<h2>Tech News</h2><p>Latest updates in the tech world...</p>"
    if "sports" in preferences:
        content += "<h2>Sports Updates</h2><p>Exciting sports events this week...</p>"
    if "entertainment" in preferences:
        content += "<h2>Entertainment Buzz</h2><p>What's new in the world of entertainment...</p>"

    content += f"""
    <p>Date: {datetime.now().strftime('%Y-%m-%d')}</p>
    <p>Stay tuned for more exciting updates tailored just for you!</p>
    """
    return content

def choose_ab_test_subject(email: str):
    # Use the email as a seed for consistent A/B testing
    random.seed(email)
    if random.random() < ab_test_config.test_percentage:
        return ab_test_config.subject_a
    else:
        return ab_test_config.subject_b

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
