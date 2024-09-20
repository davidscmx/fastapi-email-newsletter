import logging
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from models import Subscriber, Unsubscriber

from subscription_service import subscribe, unsubscribe, get_subscriber_preferences
from utils import limiter, setup_rate_limiting
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from analytics import analytics

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI()
setup_rate_limiting(app)

app.mount("/static", StaticFiles(directory="."), name="static")

scheduler = AsyncIOScheduler()


@app.on_event("startup")
async def startup_event():
    scheduler.start()
    scheduler.add_job(send_scheduled_newsletter,
                      trigger=CronTrigger(day_of_week="mon", hour=9, minute=0))
    scheduler.add_job(
        analytics.update_analytics,
        trigger=CronTrigger(hour='*'))  # Update analytics every hour


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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
