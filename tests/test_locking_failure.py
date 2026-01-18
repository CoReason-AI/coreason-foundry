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
from unittest.mock import MagicMock

import pytest
from fakeredis import FakeAsyncRedis

from coreason_foundry.locking import RedisLockRegistry


@pytest.mark.asyncio
async def test_lock_release_lua_exception() -> None:
    """
    Test that if the Lua script execution fails (e.g. Redis error),
    it is caught and logged, returning False.
    """
    fake_redis = FakeAsyncRedis()
    registry = RedisLockRegistry(fake_redis)
    project_id = uuid.uuid4()
    field = "test_field"
    user_id = uuid.uuid4()

    # Mock eval to raise Exception
    # Note: fakeredis methods are async, but mocking side_effect on async methods
    # requires setting the side_effect to an exception directly if it's awaitable?
    # No, for async mocks, side_effect=Exception works if called with await.
    # However, RedisLockRegistry calls self.redis.eval.
    # We need to ensure we mock the instance method correctly.

    # Since we passed fake_redis instance, we can mock its eval method.
    # But fake_redis.eval is an async method.

    original_eval = fake_redis.eval

    async def mock_eval(*args, **kwargs):
        raise RuntimeError("Lua Script Failed")

    fake_redis.eval = mock_eval  # type: ignore

    result = await registry.release(project_id, field, user_id)

    assert result is False

    # Restore (though fixture isolation usually handles this if we used a fixture, here we created locally)
