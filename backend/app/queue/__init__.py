from redis import Redis
from rq import Queue, Retry

from app.core.config import get_settings
from app.queue.settings import QUEUE_NAME, WEBHOOK_MAX_RETRIES, WEBHOOK_RETRY_INTERVALS


def get_redis_connection() -> Redis:
    return Redis.from_url(get_settings().redis_url)


def get_webhook_queue() -> Queue:
    return Queue(QUEUE_NAME, connection=get_redis_connection())


def webhook_retry() -> Retry:
    return Retry(max=WEBHOOK_MAX_RETRIES, interval=WEBHOOK_RETRY_INTERVALS)
