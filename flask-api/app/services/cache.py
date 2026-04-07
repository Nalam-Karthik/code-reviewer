# flask-api/app/services/cache.py

import redis
import hashlib
import json
import os

# Connect to Redis container
# decode_responses=True means we get strings back, not bytes
_redis = redis.from_url(
    os.getenv("REDIS_URL", "redis://redis:6379/0"),
    decode_responses=True
)

CACHE_TTL = 3600  # 1 hour in seconds


def make_cache_key(language: str, code: str) -> str:
    """
    Build a unique cache key from language + code.
    MD5 is fine here — we're not using it for security, just identity.
    Same code + same language always produces the same key.
    """
    raw = f"{language}::{code}"
    return "review:" + hashlib.md5(raw.encode()).hexdigest()


def make_code_hash(language: str, code: str) -> str:
    """Same hash, stored in the DB for reference."""
    return hashlib.md5(f"{language}::{code}".encode()).hexdigest()


def get_cached_review(language: str, code: str):
    """
    Return cached review dict if it exists, else None.
    Redis GET returns None if key doesn't exist.
    """
    key  = make_cache_key(language, code)
    data = _redis.get(key)

    if data:
        _redis.incr("stats:cache_hits")     # increment hit counter
        return json.loads(data)             # deserialise JSON string → dict

    _redis.incr("stats:cache_misses")       # increment miss counter
    return None


def set_cached_review(language: str, code: str, review: dict):
    """
    Store review in Redis with TTL.
    json.dumps converts the dict to a JSON string for storage.
    """
    key = make_cache_key(language, code)
    _redis.setex(key, CACHE_TTL, json.dumps(review))


def get_cache_stats() -> dict:
    """
    Return hit/miss counts — used in the /api/reviews/stats endpoint.
    These counters are stored as simple integers in Redis.
    """
    hits   = int(_redis.get("stats:cache_hits")   or 0)
    misses = int(_redis.get("stats:cache_misses") or 0)
    total  = hits + misses
    return {
        "cache_hits":   hits,
        "cache_misses": misses,
        "hit_rate":     round(hits / total, 2) if total > 0 else 0.0
    }