# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_foundry

from typing import Optional
from uuid import UUID

from redis.asyncio import Redis

from coreason_foundry.managers import LockRegistry
from coreason_foundry.utils.logger import logger


class RedisLockRegistry(LockRegistry):
    """
    Redis implementation of the LockRegistry.
    Uses 'SET key value NX EX ttl' for atomic locking.
    """

    def __init__(self, redis_client: Redis) -> None:
        self.redis = redis_client

    def _make_key(self, project_id: UUID, field: str) -> str:
        return f"lock:project:{project_id}:field:{field}"

    async def acquire(self, project_id: UUID, field: str, user_id: UUID, ttl_seconds: int = 60) -> bool:
        key = self._make_key(project_id, field)
        value = str(user_id)

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

        # We need to ensure we only delete if WE own the lock.
        # This requires a get-check-delete sequence.
        # Ideally, use a Lua script for atomicity, but for now, simple check is okay
        # provided we accept a tiny race condition (lock expires between get and delete).
        # However, checking 'get' first is safer than blind delete.

        # Better: Use Lua script.
        # "if redis.call('get', KEYS[1]) == ARGV[1] then return redis.call('del', KEYS[1]) else return 0 end"

        script = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("del", KEYS[1])
        else
            return 0
        end
        """

        result = await self.redis.eval(script, 1, key, str(user_id))  # type: ignore

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
                return UUID(value.decode("utf-8"))
            except (ValueError, AttributeError):
                # Should not happen if we only store UUID strings
                return None
        return None
