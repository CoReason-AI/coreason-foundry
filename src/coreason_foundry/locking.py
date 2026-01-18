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
    Maintains a secondary index 'lock:user:{user_id}:project:{project_id}' (Set)
    to track locks held by a user for bulk release.
    """

    def __init__(self, redis_client: Redis) -> None:
        self.redis = redis_client

    def _make_key(self, project_id: UUID, field: str) -> str:
        return f"lock:project:{project_id}:field:{field}"

    def _make_user_index_key(self, project_id: UUID, user_id: UUID) -> str:
        return f"lock:user:{user_id}:project:{project_id}"

    async def acquire(self, project_id: UUID, field: str, user_id: UUID, ttl_seconds: int = 60) -> bool:
        key = self._make_key(project_id, field)
        user_index_key = self._make_user_index_key(project_id, user_id)
        value = str(user_id)

        # Lua script to atomicity acquire lock AND add to user index
        # KEYS[1] = lock_key
        # KEYS[2] = user_index_key
        # ARGV[1] = user_id (value)
        # ARGV[2] = ttl_seconds
        # ARGV[3] = field_name (to store in set)

        script = """
        -- Try to acquire lock
        -- SET key value NX EX ttl
        local result = redis.call('set', KEYS[1], ARGV[1], 'NX', 'EX', ARGV[2])

        if result then
            -- Lock acquired, add field to user index
            redis.call('sadd', KEYS[2], ARGV[3])
            return 1
        else
            return 0
        end
        """

        result = await self.redis.eval(script, 2, key, user_index_key, value, ttl_seconds, field)

        if result == 1:
            logger.info(f"Lock acquired: {key} by {user_id}")
            return True
        else:
            logger.debug(f"Lock denied: {key} requested by {user_id}")
            return False

    async def release(self, project_id: UUID, field: str, user_id: UUID) -> bool:
        key = self._make_key(project_id, field)
        user_index_key = self._make_user_index_key(project_id, user_id)

        # Lua script to verify ownership, delete lock, and remove from index
        # KEYS[1] = lock_key
        # KEYS[2] = user_index_key
        # ARGV[1] = user_id
        # ARGV[2] = field_name

        script = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            redis.call("del", KEYS[1])
            redis.call("srem", KEYS[2], ARGV[2])
            return 1
        else
            return 0
        end
        """

        result = await self.redis.eval(script, 2, key, user_index_key, str(user_id), field)

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

    async def release_all_for_user(self, project_id: UUID, user_id: UUID) -> int:
        """
        Releases all locks held by a user in a project.
        """
        user_index_key = self._make_user_index_key(project_id, user_id)

        # We get all fields, then try to release them.
        fields = await self.redis.smembers(user_index_key)
        if not fields:
            return 0

        count = 0
        # Pipeline the releases for performance - actually iterating sequentially for safety/simplicity with eval
        for member in fields:
            field = member.decode("utf-8") if isinstance(member, bytes) else str(member)
            if await self.release(project_id, field, user_id):
                count += 1

        # Finally delete the index key (should be empty if all releases succeeded,
        # but if some failed due to expiry, we should clean up).
        # We release locks for ALL sessions of that user.
        # This is intended behavior (single user shouldn't lock against themselves).

        # So, we should clear the index.
        await self.redis.delete(user_index_key)

        return count
