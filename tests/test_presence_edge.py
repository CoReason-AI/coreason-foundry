# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_foundry

import asyncio
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from fakeredis import FakeAsyncRedis
from redis.exceptions import ConnectionError

from coreason_foundry.presence import RedisPresenceRegistry


@pytest.mark.asyncio
async def test_presence_project_isolation() -> None:
    """
    Test that presence lists are strictly isolated between projects.
    """
    fake_redis = FakeAsyncRedis()
    registry = RedisPresenceRegistry(fake_redis)

    project_a = uuid4()
    project_b = uuid4()
    user_1 = uuid4()
    user_2 = uuid4()

    # Add User 1 to Project A
    await registry.add_user(project_a, user_1)

    # Verify User 1 is in A but not B
    users_a = await registry.get_present_users(project_a)
    users_b = await registry.get_present_users(project_b)

    assert user_1 in users_a
    assert user_1 not in users_b
    assert len(users_b) == 0

    # Add User 2 to Project B
    await registry.add_user(project_b, user_2)

    # Verify User 2 is in B but not A
    users_a = await registry.get_present_users(project_a)
    users_b = await registry.get_present_users(project_b)

    assert user_2 in users_b
    assert user_2 not in users_a
    assert len(users_a) == 1

    await fake_redis.aclose()


@pytest.mark.asyncio
async def test_presence_high_concurrency() -> None:
    """
    Test adding a large number of users simultaneously to stress the registry.
    """
    fake_redis = FakeAsyncRedis()
    registry = RedisPresenceRegistry(fake_redis)
    project_id = uuid4()

    # Generate 1000 unique users
    users = [uuid4() for _ in range(1000)]

    # Add them all concurrently
    await asyncio.gather(*(registry.add_user(project_id, uid) for uid in users))

    # Verify all are present
    present_users = await registry.get_present_users(project_id)
    assert len(present_users) == 1000
    assert set(present_users) == set(users)

    await fake_redis.aclose()


@pytest.mark.asyncio
async def test_presence_rapid_flapping() -> None:
    """
    Test a single user rapidly joining and leaving a project.
    """
    fake_redis = FakeAsyncRedis()
    registry = RedisPresenceRegistry(fake_redis)
    project_id = uuid4()
    user_id = uuid4()

    # Rapidly add/remove 50 times
    for _ in range(50):
        await registry.add_user(project_id, user_id)
        users_mid = await registry.get_present_users(project_id)
        assert user_id in users_mid

        await registry.remove_user(project_id, user_id)
        users_end = await registry.get_present_users(project_id)
        assert user_id not in users_end

    await fake_redis.aclose()


@pytest.mark.asyncio
async def test_redis_connection_failure() -> None:
    """
    Test that Redis connection errors are propagated up.
    The Registry is designed to fail loudly so the caller handles it (e.g. 500 Error).
    """
    # Create a mock redis client that raises ConnectionError on sadd
    mock_redis = MagicMock()
    # Mocking an async method requires returning a future or being an async mock
    # easiest way is to use an AsyncMock if available or just patch the method on a real object

    # Let's use FakeRedis but patch the sadd method
    fake_redis = FakeAsyncRedis()

    # We need to monkeypatch the sadd method of the underlying redis client
    # But checking if fakeredis supports side_effect on methods easily

    # Alternative: Use a pure Mock object instead of FakeRedis for this specific test
    mock_redis = MagicMock()
    # Configure async methods
    future: asyncio.Future[None] = asyncio.Future()
    future.set_exception(ConnectionError("Redis is down"))
    mock_redis.sadd.return_value = future

    registry_broken = RedisPresenceRegistry(mock_redis)

    with pytest.raises(ConnectionError):
        await registry_broken.add_user(uuid4(), uuid4())

    await fake_redis.aclose()
