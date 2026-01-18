# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_foundry

import pytest
from uuid import uuid4
from unittest.mock import MagicMock
from redis.asyncio import Redis
from coreason_foundry.locking import RedisLockRegistry

@pytest.fixture
def mock_redis():
    """
    Returns a fakeredis instance or a MagicMock that behaves like redis-py.
    Since we need Lua scripting, we should use fakeredis if available and configured with lua support,
    or mock the eval method if the logic is simple enough (but Lua logic is complex).

    fakeredis with lupa is required for Lua.
    """
    try:
        import fakeredis.aioredis
        # Create a new FakeRedis instance
        return fakeredis.aioredis.FakeRedis(decode_responses=False)
    except ImportError:
        # Fallback to MagicMock if fakeredis is not installed (should not happen in this env)
        return MagicMock(spec=Redis)

@pytest.mark.asyncio
async def test_acquire_creates_index(mock_redis):
    registry = RedisLockRegistry(mock_redis)
    project_id = uuid4()
    user_id = uuid4()
    field = "system_prompt"

    # Acquire
    result = await registry.acquire(project_id, field, user_id)
    assert result is True

    # Check lock key
    lock_key = f"lock:project:{project_id}:field:{field}"
    assert await mock_redis.get(lock_key) == str(user_id).encode()

    # Check index key
    index_key = f"lock:user:{user_id}:project:{project_id}"
    members = await mock_redis.smembers(index_key)
    assert field.encode() in members

@pytest.mark.asyncio
async def test_release_updates_index(mock_redis):
    registry = RedisLockRegistry(mock_redis)
    project_id = uuid4()
    user_id = uuid4()
    field = "system_prompt"

    # Acquire first
    await registry.acquire(project_id, field, user_id)

    # Release
    result = await registry.release(project_id, field, user_id)
    assert result is True

    # Check lock key gone
    lock_key = f"lock:project:{project_id}:field:{field}"
    assert await mock_redis.get(lock_key) is None

    # Check index key updated
    index_key = f"lock:user:{user_id}:project:{project_id}"
    members = await mock_redis.smembers(index_key)
    assert field.encode() not in members

@pytest.mark.asyncio
async def test_release_all_for_user(mock_redis):
    registry = RedisLockRegistry(mock_redis)
    project_id = uuid4()
    user_id = uuid4()
    fields = ["field1", "field2", "field3"]

    # Acquire multiple locks
    for field in fields:
        await registry.acquire(project_id, field, user_id)

    # Verify index has all
    index_key = f"lock:user:{user_id}:project:{project_id}"
    members = await mock_redis.smembers(index_key)
    assert len(members) == 3

    # Release all
    count = await registry.release_all_for_user(project_id, user_id)
    assert count == 3

    # Verify all locks gone
    for field in fields:
        lock_key = f"lock:project:{project_id}:field:{field}"
        assert await mock_redis.get(lock_key) is None

    # Verify index key gone
    assert await mock_redis.exists(index_key) == 0

@pytest.mark.asyncio
async def test_release_all_handles_expired_locks(mock_redis):
    registry = RedisLockRegistry(mock_redis)
    project_id = uuid4()
    user_id = uuid4()
    field = "expired_field"

    # Acquire with short TTL (simulate expiry)
    await registry.acquire(project_id, field, user_id, ttl_seconds=1)

    # Manually delete the lock key to simulate expiry
    lock_key = f"lock:project:{project_id}:field:{field}"
    await mock_redis.delete(lock_key)

    # Index still has the field (because expiry doesn't trigger index cleanup automatically)
    index_key = f"lock:user:{user_id}:project:{project_id}"
    members = await mock_redis.smembers(index_key)
    assert field.encode() in members

    # Release all
    count = await registry.release_all_for_user(project_id, user_id)

    # Should be 0 because lock was already gone (release checks ownership)
    assert count == 0

    # BUT index should be cleaned up
    assert await mock_redis.exists(index_key) == 0
