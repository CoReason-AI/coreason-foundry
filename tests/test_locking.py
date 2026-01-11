# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_foundry

import uuid

import pytest
from fakeredis import FakeAsyncRedis

from coreason_foundry.locking import RedisLockRegistry


@pytest.fixture
def redis_client() -> FakeAsyncRedis:
    return FakeAsyncRedis()


@pytest.fixture
def lock_registry(redis_client: FakeAsyncRedis) -> RedisLockRegistry:
    return RedisLockRegistry(redis_client)


@pytest.mark.asyncio
async def test_acquire_lock_success(lock_registry: RedisLockRegistry) -> None:
    project_id = uuid.uuid4()
    user_id = uuid.uuid4()
    field = "system_prompt"

    result = await lock_registry.acquire(project_id, field, user_id)
    assert result is True

    owner = await lock_registry.get_lock_owner(project_id, field)
    assert owner == user_id


@pytest.mark.asyncio
async def test_acquire_lock_fail_already_locked(lock_registry: RedisLockRegistry) -> None:
    project_id = uuid.uuid4()
    user1 = uuid.uuid4()
    user2 = uuid.uuid4()
    field = "system_prompt"

    # User 1 acquires
    await lock_registry.acquire(project_id, field, user1)

    # User 2 tries to acquire
    result = await lock_registry.acquire(project_id, field, user2)
    assert result is False

    # Owner should still be User 1
    owner = await lock_registry.get_lock_owner(project_id, field)
    assert owner == user1


@pytest.mark.asyncio
async def test_release_lock_success(lock_registry: RedisLockRegistry) -> None:
    project_id = uuid.uuid4()
    user_id = uuid.uuid4()
    field = "system_prompt"

    await lock_registry.acquire(project_id, field, user_id)

    result = await lock_registry.release(project_id, field, user_id)
    assert result is True

    owner = await lock_registry.get_lock_owner(project_id, field)
    assert owner is None


@pytest.mark.asyncio
async def test_release_lock_fail_not_owner(lock_registry: RedisLockRegistry) -> None:
    project_id = uuid.uuid4()
    user1 = uuid.uuid4()
    user2 = uuid.uuid4()
    field = "system_prompt"

    await lock_registry.acquire(project_id, field, user1)

    # User 2 tries to release User 1's lock
    result = await lock_registry.release(project_id, field, user2)
    assert result is False

    # Lock should still be held by User 1
    owner = await lock_registry.get_lock_owner(project_id, field)
    assert owner == user1


@pytest.mark.asyncio
async def test_release_lock_fail_no_lock(lock_registry: RedisLockRegistry) -> None:
    project_id = uuid.uuid4()
    user_id = uuid.uuid4()
    field = "system_prompt"

    # Try to release a lock that doesn't exist
    result = await lock_registry.release(project_id, field, user_id)
    assert result is False


@pytest.mark.asyncio
async def test_lock_expiration(lock_registry: RedisLockRegistry) -> None:
    import asyncio

    project_id = uuid.uuid4()
    user_id = uuid.uuid4()
    field = "system_prompt"
    ttl = 1  # 1 second

    await lock_registry.acquire(project_id, field, user_id, ttl_seconds=ttl)

    # Verify locked
    assert await lock_registry.get_lock_owner(project_id, field) == user_id

    # Wait for expiration
    await asyncio.sleep(1.1)

    # Should be unlocked
    assert await lock_registry.get_lock_owner(project_id, field) is None
