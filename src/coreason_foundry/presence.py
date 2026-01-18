# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_foundry

from typing import List
from uuid import UUID

from redis.asyncio import Redis

from coreason_foundry.interfaces import PresenceRegistry
from coreason_foundry.utils.logger import logger


class RedisPresenceRegistry(PresenceRegistry):
    """
    Redis implementation of the PresenceRegistry.
    Uses 'SADD key member' for tracking presence.
    """

    def __init__(self, redis_client: Redis) -> None:
        self.redis = redis_client

    def _make_key(self, project_id: UUID) -> str:
        return f"presence:project:{project_id}"

    async def add_user(self, project_id: UUID, user_id: UUID) -> None:
        key = self._make_key(project_id)
        # SADD returns 1 if new element, 0 if already existed
        await self.redis.sadd(key, str(user_id))
        logger.debug(f"User {user_id} added to presence list for project {project_id}")

    async def remove_user(self, project_id: UUID, user_id: UUID) -> None:
        key = self._make_key(project_id)
        # SREM returns 1 if removed, 0 if not found
        await self.redis.srem(key, str(user_id))
        logger.debug(f"User {user_id} removed from presence list for project {project_id}")

    async def get_present_users(self, project_id: UUID) -> List[UUID]:
        key = self._make_key(project_id)
        members = await self.redis.smembers(key)

        users = []
        for member in members:
            try:
                # members come back as bytes or strings depending on client decoding
                # default client decodes if decode_responses=True, but safer to assume bytes/str hybrid
                s = member.decode("utf-8") if isinstance(member, bytes) else str(member)
                users.append(UUID(s))
            except (ValueError, AttributeError):
                # Gracefully handle corrupted data
                logger.warning(f"Corrupted presence data in {key}: {member}")
                continue

        return users
