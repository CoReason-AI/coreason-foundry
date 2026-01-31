# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_foundry

from unittest.mock import AsyncMock, patch

import pytest
from coreason_foundry.api.app import app
from fastapi.testclient import TestClient


@pytest.mark.asyncio
async def test_app_lifespan() -> None:
    # Mock get_redis_client to verify close is called
    with patch("coreason_foundry.api.app.get_redis_client") as mock_get_redis:
        mock_redis = AsyncMock()
        mock_get_redis.return_value = mock_redis

        with TestClient(app):
            # Trigger startup
            pass

        # Trigger shutdown
        mock_redis.aclose.assert_called_once()
