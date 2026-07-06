import redis
import json
from app.core.config import settings

REDIS_URL = settings.REDIS_URL

# Try to connect — if Redis isn't running, app still works
try:
    r = redis.from_url(REDIS_URL, decode_responses=True, socket_connect_timeout=2)
    r.ping()
    cache_available = True
    print("✅ Redis cache connected")
except Exception:
    cache_available = False
    r = None
    print("⚠️ Redis not available — running without cache (this is OK)")


def cache_set(key: str, value, ttl: int = 3600):
    """Store value in cache for ttl seconds"""
    if not cache_available:
        return
    try:
        r.setex(key, ttl, json.dumps(value))
    except Exception:
        pass


def cache_get(key: str):
    """Get value from cache, returns None if missing"""
    if not cache_available:
        return None
    try:
        data = r.get(key)
        return json.loads(data) if data else None
    except Exception:
        return None


def cache_delete(key: str):
    """Remove a key from cache"""
    if not cache_available:
        return
    try:
        r.delete(key)
    except Exception:
        pass