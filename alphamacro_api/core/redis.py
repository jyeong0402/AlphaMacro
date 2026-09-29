"""Redis connection and cache helpers."""
import json
from typing import Any
from .config import settings

try:
    import redis
except ImportError:  # pragma: no cover
    redis = None

client = redis.Redis.from_url(settings.redis_url, decode_responses=True) if redis else None
redis_error = redis.exceptions.RedisError if redis else OSError


def get_cache(key: str) -> Any | None:
    if not client:
        return None
    try:
        value = client.get(key)
    except (redis_error, ValueError):
        return None
    return json.loads(value) if value else None


def set_cache(key: str, value: Any, ttl: int = 300) -> bool:
    if not client:
        return False
    try:
        return bool(client.setex(key, ttl, json.dumps(value, default=str)))
    except (redis_error, TypeError, ValueError):
        return False


def ping() -> bool:
    if not client:
        return False
    try:
        return bool(client.ping())
    except redis_error:
        return False
