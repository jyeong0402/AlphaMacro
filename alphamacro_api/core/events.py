"""Small alert event broker with Redis pub/sub and an in-process fallback."""
import asyncio
import json
from typing import Any
from .redis import client, redis_error

ALERT_CHANNEL = "alphamacro:alerts"
_local_subscribers: set[asyncio.Queue[dict[str, Any]]] = set()


def _publish_redis(payload: str) -> bool:
    if not client:
        return False
    try:
        return bool(client.publish(ALERT_CHANNEL, payload))
    except (redis_error, ValueError):
        return False


async def publish_alert(event: dict[str, Any]) -> None:
    """Publish without making an alert write fail when Redis is unavailable."""
    payload = json.dumps(event, default=str)
    if await asyncio.to_thread(_publish_redis, payload):
        return
    for queue in tuple(_local_subscribers):
        queue.put_nowait(event)


async def subscribe_alerts() -> tuple[asyncio.Queue[dict[str, Any]], Any | None]:
    """Return a local queue and, when available, a Redis pub/sub subscription."""
    queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
    _local_subscribers.add(queue)
    pubsub = None
    if client:
        try:
            pubsub = client.pubsub()
            await asyncio.to_thread(pubsub.subscribe, ALERT_CHANNEL)
        except (redis_error, ValueError):
            if pubsub:
                pubsub.close()
            pubsub = None
    return queue, pubsub


async def unsubscribe_alerts(queue: asyncio.Queue, pubsub: Any | None) -> None:
    _local_subscribers.discard(queue)
    if pubsub:
        try:
            await asyncio.to_thread(pubsub.close)
        except (redis_error, ValueError):
            pass
