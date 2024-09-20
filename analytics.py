import logging
from datetime import datetime, timedelta
from subscription_service import get_subscribers

logger = logging.getLogger(__name__)

class SubscriptionAnalytics:
    def __init__(self):
        self.last_update = None
        self.total_subscribers = 0
        self.active_subscribers = 0
        self.unsubscribed = 0
        self.new_subscribers = 0
        self.new_unsubscribers = 0

    async def update_analytics(self):
        current_time = datetime.now().replace(tzinfo=None)
        subscribers = await get_subscribers()

        self.total_subscribers = len(subscribers)
        self.active_subscribers = sum(1 for sub in subscribers if not sub.get('unsubscribed', False))
        self.unsubscribed = self.total_subscribers - self.active_subscribers

        if self.last_update:
            time_diff = current_time - self.last_update
            self.new_subscribers = sum(1 for sub in subscribers if datetime.fromisoformat(sub['created_at'].replace('Z', '+00:00')).replace(tzinfo=None) > self.last_update)
            self.new_unsubscribers = sum(1 for sub in subscribers if sub.get('unsubscribed', False) and 'updated_at' in sub and datetime.fromisoformat(sub['updated_at'].replace('Z', '+00:00')).replace(tzinfo=None) > self.last_update)
        else:
            self.new_subscribers = self.total_subscribers
            self.new_unsubscribers = self.unsubscribed

        self.last_update = current_time
        logger.info(f"Analytics updated: Total: {self.total_subscribers}, Active: {self.active_subscribers}, Unsubscribed: {self.unsubscribed}, New: {self.new_subscribers}, New Unsubscribers: {self.new_unsubscribers}")

    def get_analytics_report(self):
        return {
            "total_subscribers": self.total_subscribers,
            "active_subscribers": self.active_subscribers,
            "unsubscribed": self.unsubscribed,
            "new_subscribers": self.new_subscribers,
            "new_unsubscribers": self.new_unsubscribers,
            "last_update": self.last_update.isoformat() if self.last_update else None
        }

analytics = SubscriptionAnalytics()
