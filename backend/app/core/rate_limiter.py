import time
import math
import uuid
import logging
from typing import Tuple
from app.core.redis import get_redis_client

logger = logging.getLogger("gateway.rate_limiter")

# Redis Lua Script for Atomic Sliding-Window Rate Limiting using Sorted Sets (ZSET)
SLIDING_WINDOW_LUA_SCRIPT = """
local key = KEYS[1]
local now = tonumber(ARGV[1])
local window_ms = tonumber(ARGV[2])
local max_limit = tonumber(ARGV[3])
local member = ARGV[4]

local clear_before = now - window_ms
redis.call('ZREMRANGEBYSCORE', key, 0, clear_before)

local current_count = redis.call('ZCARD', key)

if current_count < max_limit then
    redis.call('ZADD', key, now, member)
    local expire_time = math.ceil(window_ms / 1000) + 2
    redis.call('EXPIRE', key, expire_time)
    local remaining = max_limit - current_count - 1
    return {1, remaining, math.floor(window_ms / 1000)}
else
    local oldest = redis.call('ZRANGE', key, 0, 0, 'WITHSCORES')
    local reset_after = 1
    if oldest and #oldest >= 2 then
        local oldest_ts = tonumber(oldest[2])
        reset_after = math.max(1, math.ceil((oldest_ts + window_ms - now) / 1000))
    end
    return {0, 0, reset_after}
end
"""


class SlidingWindowRateLimiter:
    """
    Atomic Sliding-Window Rate Limiter powered by Redis Lua and Sorted Sets (ZSET).
    Calculates moving window rate limits with sub-millisecond overhead.
    """

    async def check_rate_limit(
        self,
        identifier: str,
        max_requests: int = 60,
        window_seconds: int = 60,
    ) -> Tuple[bool, int, int]:
        """
        Evaluates sliding window limit for the given identifier.

        Args:
            identifier: Unique key identifier (e.g. `tenant_id:key_hash`)
            max_requests: Maximum allowed requests within the window
            window_seconds: Sliding window duration in seconds (default: 60s)

        Returns:
            Tuple of (allowed: bool, remaining: int, retry_after_seconds: int)
        """
        if max_requests <= 0:
            return True, 999999, 0

        r = await get_redis_client()
        key = f"ratelimit:{identifier}"
        now_ms = int(time.time() * 1000)
        window_ms = window_seconds * 1000
        req_member = f"{now_ms}:{uuid.uuid4().hex[:8]}"

        # 1. Try atomic Redis Lua script (Production Redis 7)
        try:
            result = await r.eval(
                SLIDING_WINDOW_LUA_SCRIPT,
                1,
                key,
                str(now_ms),
                str(window_ms),
                str(max_requests),
                req_member,
            )
            if result and isinstance(result, (list, tuple)) and len(result) >= 3:
                allowed = bool(result[0])
                remaining = int(result[1])
                retry_after = int(result[2])
                return allowed, remaining, retry_after
        except Exception as e:
            logger.debug(f"Lua eval skipped/unsupported ({e}), falling back to pipeline")

        # 2. Redis Pipeline fallback (for testing/environments without Lua c-extensions)
        try:
            clear_before = now_ms - window_ms
            pipe = r.pipeline(transaction=True)
            pipe.zremrangebyscore(key, 0, clear_before)
            pipe.zcard(key)
            pipe_res = await pipe.execute()
            current_count = int(pipe_res[1])

            if current_count < max_requests:
                pipe2 = r.pipeline(transaction=True)
                pipe2.zadd(key, {req_member: now_ms})
                pipe2.expire(key, math.ceil(window_seconds) + 2)
                await pipe2.execute()
                remaining = max_requests - current_count - 1
                return True, max(0, remaining), window_seconds
            else:
                oldest_list = await r.zrange(key, 0, 0, withscores=True)
                reset_after = 1
                if oldest_list:
                    oldest_ts = float(oldest_list[0][1])
                    reset_after = max(1, math.ceil((oldest_ts + window_ms - now_ms) / 1000))
                return False, 0, reset_after

        except Exception as pe:
            logger.error(f"Rate limiter pipeline error: {pe}")
            return True, max_requests, 0


rate_limiter = SlidingWindowRateLimiter()
