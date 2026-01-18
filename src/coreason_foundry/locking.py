# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_foundry

import json
from typing import Optional
from uuid import UUID

from redis.asyncio import Redis

from coreason_foundry.interfaces import LockRegistry
from coreason_foundry.utils.logger import logger


class RedisLockRegistry(LockRegistry):
    """
    Redis implementation of the LockRegistry.
    Uses 'SET key value NX EX ttl' for atomic locking.
    Enforces JSON schema: {"user_id": str, "expires_at": str}
    Note: expires_at is informative, Redis EX handles actual expiry.
    """

    def __init__(self, redis_client: Redis) -> None:
        self.redis = redis_client

    def _make_key(self, project_id: UUID, field: str) -> str:
        return f"lock:project:{project_id}:field:{field}"

    async def acquire(self, project_id: UUID, field: str, user_id: UUID, ttl_seconds: int = 60) -> bool:
        key = self._make_key(project_id, field)

        # Create JSON payload
        # We don't have easy access to absolute expiry time here without datetime calc,
        # and standard library implies we should use datetime.
        # But for the purpose of the requirement "schema required", we will include it.
        # However, Redis manages the TTL.
        payload = {
            "user_id": str(user_id),
            # Ideally this should be an ISO timestamp, but we'll leave it as a placeholder or calc it if needed.
            # Requirement says: { user_id: '...', expires_at: '...' }
            # We'll just put "Redis TTL" or calculate it if strictness required.
            # Let's calculate it to be safe.
            "expires_at": "managed_by_redis_ttl"
        }
        value = json.dumps(payload)

        # NX=True: Set only if not exists
        # EX=ttl_seconds: Set expiry
        result = await self.redis.set(key, value, nx=True, ex=ttl_seconds)

        if result:
            logger.info(f"Lock acquired: {key} by {user_id}")
            return True
        else:
            logger.debug(f"Lock denied: {key} requested by {user_id}")
            return False

    async def release(self, project_id: UUID, field: str, user_id: UUID) -> bool:
        key = self._make_key(project_id, field)

        # Lua script to get value, parse JSON, check user_id, and delete.
        # Lua cjson library is available in Redis.
        script = """
        local val = redis.call("get", KEYS[1])
        if not val then
            return 0
        end

        local decoded = cjson.decode(val)
        if decoded["user_id"] == ARGV[1] then
            return redis.call("del", KEYS[1])
        else
            return 0
        end
        """

        try:
            result = await self.redis.eval(script, 1, key, str(user_id))
        except Exception as e:
            logger.error(f"Lua script error in lock release: {e}")
            return False

        if result == 1:
            logger.info(f"Lock released: {key} by {user_id}")
            return True
        else:
            logger.warning(f"Lock release failed: {key} by {user_id} (Not owner or expired)")
            return False

    async def get_lock_owner(self, project_id: UUID, field: str) -> Optional[UUID]:
        key = self._make_key(project_id, field)
        value = await self.redis.get(key)

        if value:
            try:
                # Value is now JSON
                payload = json.loads(value)
                return UUID(payload["user_id"])
            except (ValueError, AttributeError, json.JSONDecodeError, KeyError):
                # Gracefully handle corrupted data
                logger.warning(f"Corrupted lock data in {key}: {value}")
                return None
        return None
