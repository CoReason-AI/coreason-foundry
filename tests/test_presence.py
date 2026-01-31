# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_foundry

from uuid import uuid4

import pytest
from coreason_foundry.memory import InMemoryPresenceRegistry
from coreason_foundry.presence import RedisPresenceRegistry
from fakeredis import FakeAsyncRedis


@pytest.mark.asyncio
async def test_in_memory_presence_registry() -> None:
    """
    Test InMemoryPresenceRegistry basic functionality.
    """
    registry = InMemoryPresenceRegistry()
    project_id = uuid4()
    user_a = uuid4()
    user_b = uuid4()

    # 1. Add User A
    await registry.add_user(project_id, user_a)
    users = await registry.get_present_users(project_id)
    assert len(users) == 1
    assert user_a in users

    # 2. Add User B
    await registry.add_user(project_id, user_b)
    users = await registry.get_present_users(project_id)
    assert len(users) == 2
    assert user_a in users
    assert user_b in users

    # 3. Add User A again (idempotency)
    await registry.add_user(project_id, user_a)
    users = await registry.get_present_users(project_id)
    assert len(users) == 2

    # 4. Remove User A
    await registry.remove_user(project_id, user_a)
    users = await registry.get_present_users(project_id)
    assert len(users) == 1
    assert user_b in users

    # 5. Remove User B
    await registry.remove_user(project_id, user_b)
    users = await registry.get_present_users(project_id)
    assert len(users) == 0


@pytest.mark.asyncio
async def test_redis_presence_registry() -> None:
    """
    Test RedisPresenceRegistry using fakeredis.
    """
    # Setup FakeRedis
    fake_redis = FakeAsyncRedis()
    registry = RedisPresenceRegistry(fake_redis)

    project_id = uuid4()
    user_a = uuid4()
    user_b = uuid4()

    # 1. Add User A
    await registry.add_user(project_id, user_a)
    users = await registry.get_present_users(project_id)
    assert len(users) == 1
    assert user_a in users

    # 2. Add User B
    await registry.add_user(project_id, user_b)
    users = await registry.get_present_users(project_id)
    assert len(users) == 2
    assert user_a in users
    assert user_b in users

    # 3. Add User A again (idempotency)
    await registry.add_user(project_id, user_a)
    users = await registry.get_present_users(project_id)
    assert len(users) == 2

    # 4. Remove User A
    await registry.remove_user(project_id, user_a)
    users = await registry.get_present_users(project_id)
    assert len(users) == 1
    assert user_b in users

    # 5. Remove User B
    await registry.remove_user(project_id, user_b)
    users = await registry.get_present_users(project_id)
    assert len(users) == 0

    # Teardown
    await fake_redis.aclose()


@pytest.mark.asyncio
async def test_redis_presence_registry_corruption() -> None:
    """
    Test that RedisPresenceRegistry handles corrupted data gracefully.
    """
    fake_redis = FakeAsyncRedis()
    registry = RedisPresenceRegistry(fake_redis)

    project_id = uuid4()
    key = registry._make_key(project_id)

    # Inject bad data directly into Redis
    await fake_redis.sadd(key, "not-a-uuid")
    await fake_redis.sadd(key, str(uuid4()))

    users = await registry.get_present_users(project_id)
    assert len(users) == 1  # Should only contain the valid UUID

    await fake_redis.aclose()
