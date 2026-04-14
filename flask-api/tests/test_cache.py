# flask-api/tests/test_cache.py

import pytest
from unittest.mock import patch, MagicMock
from app.services.cache import make_cache_key, make_code_hash


class TestCacheKeys:
    """Tests for cache key generation — no Redis needed."""

    def test_same_input_same_key(self):
        """Same language + code always produces same key."""
        key1 = make_cache_key("python", "def foo(): pass")
        key2 = make_cache_key("python", "def foo(): pass")
        assert key1 == key2

    def test_different_language_different_key(self):
        """Same code in different language = different key."""
        key_py = make_cache_key("python",     "function foo() {}")
        key_js = make_cache_key("javascript", "function foo() {}")
        assert key_py != key_js

    def test_different_code_different_key(self):
        """Different code = different key."""
        key1 = make_cache_key("python", "def foo(): pass")
        key2 = make_cache_key("python", "def bar(): pass")
        assert key1 != key2

    def test_key_has_prefix(self):
        """Cache key starts with 'review:' prefix."""
        key = make_cache_key("python", "def foo(): pass")
        assert key.startswith("review:")

    def test_code_hash_is_hex(self):
        """Code hash is a valid hex string."""
        h = make_code_hash("python", "def foo(): pass")
        assert len(h) == 32
        int(h, 16)   # raises ValueError if not valid hex


class TestCacheOperations:
    """Tests for Redis cache get/set — mocking Redis."""

    @patch("app.services.cache._redis")
    def test_cache_miss_returns_none(self, mock_redis):
        """Cache miss (key not in Redis) returns None."""
        from app.services.cache import get_cached_review
        mock_redis.get.return_value = None
        result = get_cached_review("python", "def foo(): pass")
        assert result is None

    @patch("app.services.cache._redis")
    def test_cache_hit_returns_data(self, mock_redis):
        """Cache hit returns deserialized dict."""
        import json
        from app.services.cache import get_cached_review

        cached = {"review_id": 1, "score": 80, "cached": True}
        mock_redis.get.return_value = json.dumps(cached)

        result = get_cached_review("python", "def foo(): pass")
        assert result["score"]     == 80
        assert result["review_id"] == 1

    @patch("app.services.cache._redis")
    def test_cache_increments_hit_counter(self, mock_redis):
        """Cache hit increments the Redis hit counter."""
        import json
        from app.services.cache import get_cached_review

        mock_redis.get.return_value = json.dumps({"score": 50})
        get_cached_review("python", "def foo(): pass")
        mock_redis.incr.assert_called_with("stats:cache_hits")

    @patch("app.services.cache._redis")
    def test_cache_increments_miss_counter(self, mock_redis):
        """Cache miss increments the Redis miss counter."""
        from app.services.cache import get_cached_review

        mock_redis.get.return_value = None
        get_cached_review("python", "def foo(): pass")
        mock_redis.incr.assert_called_with("stats:cache_misses")