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
async def test_lock_namespace_isolation(lock_registry: RedisLockRegistry) -> None:
    """
    Verify that locks are strictly isolated by Project ID and Field Name.
    A lock on (P1, F1) should NOT block (P2, F1) or (P1, F2).
    """
    p1 = uuid.uuid4()
    p2 = uuid.uuid4()
    f1 = "system_prompt"
    f2 = "user_prompt"
    user_a = uuid.uuid4()
    user_b = uuid.uuid4()

    # User A locks P1:F1
    assert await lock_registry.acquire(p1, f1, user_a) is True

    # User B should be able to lock P2:F1 (Different Project)
    assert await lock_registry.acquire(p2, f1, user_b) is True

    # User B should be able to lock P1:F2 (Same Project, Different Field)
    assert await lock_registry.acquire(p1, f2, user_b) is True

    # User B should NOT be able to lock P1:F1 (Same Project, Same Field)
    assert await lock_registry.acquire(p1, f1, user_b) is False


@pytest.mark.asyncio
async def test_concurrent_acquisition(lock_registry: RedisLockRegistry) -> None:
    """
    Simulate a high-concurrency race condition where 50 users try to acquire
    the exact same lock simultaneously.
    Only ONE should succeed.
    """
    project_id = uuid.uuid4()
    field = "shared_config"

    # Create 50 unique users
    users = [uuid.uuid4() for _ in range(50)]

    # Launch 50 simultaneous acquire requests
    tasks = [lock_registry.acquire(project_id, field, u) for u in users]
    results = await asyncio.gather(*tasks)

    # Count successes
    successes = [r for r in results if r is True]

    assert len(successes) == 1, f"Expected exactly 1 successful lock acquisition, got {len(successes)}"

    # Verify the lock owner matches one of the users
    owner = await lock_registry.get_lock_owner(project_id, field)
    assert owner in users


@pytest.mark.asyncio
async def test_zombie_release_safety(lock_registry: RedisLockRegistry) -> None:
    """
    Verify the 'Zombie Release' scenario:
    1. User A acquires lock.
    2. Lock expires.
    3. User B acquires the lock.
    4. User A (who thinks they still have it) tries to release.

    Expectation: User A's release fails. User B's lock remains intact.
    """
    project_id = uuid.uuid4()
    field = "critical_section"
    user_a = uuid.uuid4()
    user_b = uuid.uuid4()

    # 1. User A acquires with short TTL
    ttl = 1  # 1 second
    await lock_registry.acquire(project_id, field, user_a, ttl_seconds=ttl)

    # 2. Wait for expiration (simulated sleep)
    await asyncio.sleep(1.1)

    # Verify unlocked
    assert await lock_registry.get_lock_owner(project_id, field) is None

    # 3. User B acquires
    await lock_registry.acquire(project_id, field, user_b, ttl_seconds=60)
    assert await lock_registry.get_lock_owner(project_id, field) == user_b

    # 4. User A tries to release (Zombie Release)
    release_result = await lock_registry.release(project_id, field, user_a)

    # Expectation: Release denied because owner doesn't match
    assert release_result is False

    # 5. Verify User B still holds the lock
    assert await lock_registry.get_lock_owner(project_id, field) == user_b


@pytest.mark.asyncio
async def test_reacquisition_fails(lock_registry: RedisLockRegistry) -> None:
    """
    Verify current behavior: Re-acquiring a lock you already hold fails
    (because of SET NX).
    This confirms we don't support lock extension/heartbeat yet.
    """
    project_id = uuid.uuid4()
    field = "system_prompt"
    user_id = uuid.uuid4()

    # Acquire first time
    assert await lock_registry.acquire(project_id, field, user_id) is True

    # Try to acquire again
    assert await lock_registry.acquire(project_id, field, user_id) is False
