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
from typing import Any

import pytest
from coreason_foundry.locking import RedisLockRegistry
from fakeredis import FakeAsyncRedis


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
    # Since we passed fake_redis instance, we can mock its eval method.
    # But fake_redis.eval is an async method.

    async def mock_eval(*args: Any, **kwargs: Any) -> Any:
        raise RuntimeError("Lua Script Failed")

    fake_redis.eval = mock_eval

    result = await registry.release(project_id, field, user_id)

    assert result is False
