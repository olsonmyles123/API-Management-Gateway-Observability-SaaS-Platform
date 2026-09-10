import json
import logging
from typing import Optional, Dict, Any
import redis.asyncio as aioredis
from app.config import settings

logger = logging.getLogger("gateway.redis")

_redis_client: Optional[aioredis.Redis] = None


async def get_redis_client() -> aioredis.Redis:
    """
    Returns an async Redis client.
    Connects to configured REDIS_URL with fallback to fakeredis for local testing if server is unreachable.
    """
    global _redis_client
    if _redis_client is None:
        try:
            client = aioredis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
                socket_timeout=2.0,
                socket_connect_timeout=2.0,
                max_connections=50,
            )
            # Test connection
            await client.ping()
            _redis_client = client
            logger.info(f"Connected to Redis at {settings.REDIS_URL}")
        except Exception as e:
            logger.warning(f"Failed to connect to Redis server ({e}). Falling back to FakeRedis in-memory instance for testing/local run.")
            try:
                import fakeredis.aioredis
                _redis_client = fakeredis.aioredis.FakeRedis(decode_responses=True)
            except Exception as fe:
                logger.error(f"Failed to initialize fakeredis: {fe}")
                raise
    return _redis_client


async def close_redis_client():
    """Closes active Redis client connection pool."""
    global _redis_client
    if _redis_client is not None:
        try:
            await _redis_client.aclose()
        except Exception:
            pass
        _redis_client = None


async def get_cached_key_metadata(key_hash: str) -> Optional[Dict[str, Any]]:
    """
    Retrieves cached API key metadata from Redis.
    Zero PostgreSQL queries occur during live request proxying when cached.
    """
    try:
        r = await get_redis_client()
        cache_key = f"{settings.REDIS_KEY_CACHE_PREFIX}{key_hash}"
        data = await r.get(cache_key)
        if data:
            return json.loads(data)
    except Exception as e:
        logger.error(f"Redis get_cached_key_metadata error: {e}")
    return None


async def set_cached_key_metadata(key_hash: str, metadata: Dict[str, Any], ttl: Optional[int] = None) -> bool:
    """
    Caches API key metadata in Redis.
    """
    try:
        r = await get_redis_client()
        cache_key = f"{settings.REDIS_KEY_CACHE_PREFIX}{key_hash}"
        ttl_val = ttl if ttl is not None else settings.REDIS_CACHE_TTL_SECONDS
        await r.set(cache_key, json.dumps(metadata), ex=ttl_val)
        return True
    except Exception as e:
        logger.error(f"Redis set_cached_key_metadata error: {e}")
        return False


async def invalidate_key_metadata(key_hash: str) -> bool:
    """
    Actively invalidates the cached key metadata immediately upon revocation.
    """
    try:
        r = await get_redis_client()
        cache_key = f"{settings.REDIS_KEY_CACHE_PREFIX}{key_hash}"
        await r.delete(cache_key)
        return True
    except Exception as e:
        logger.error(f"Redis invalidate_key_metadata error: {e}")
        return False


async def push_telemetry_stream(event: Dict[str, Any]) -> Optional[str]:
    """
    Pushes request telemetry metadata to Redis Stream (non-blocking).
    """
    try:
        r = await get_redis_client()
        # Convert values to strings for redis stream compatibility
        stream_payload = {k: str(v) if not isinstance(v, (str, int, float, bool)) else str(v) for k, v in event.items()}
        msg_id = await r.xadd(settings.REDIS_STREAM_KEY, stream_payload, maxlen=100000, approximate=True)
        return msg_id
    except Exception as e:
        logger.error(f"Failed to push telemetry event to Redis Stream: {e}")
        return None
