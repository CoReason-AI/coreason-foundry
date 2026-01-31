# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_foundry

from unittest.mock import patch
from uuid import uuid4

import pytest
from coreason_foundry.api.dependencies import get_redis_client
from coreason_foundry.api.routes import realtime
from fakeredis.aioredis import FakeRedis
from fastapi import FastAPI
from fastapi.testclient import TestClient


@pytest.fixture
def app() -> FastAPI:
    app = FastAPI()
    app.include_router(realtime.router)
    return app


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    fake_redis = FakeRedis(decode_responses=True)
    app.dependency_overrides[get_redis_client] = lambda: fake_redis
    return TestClient(app)


def test_websocket_connection(client: TestClient) -> None:
    project_id = uuid4()
    user_id = uuid4()

    with client.websocket_connect(f"/ws/projects/{project_id}?user_id={user_id}") as websocket:
        # Check for initial broadcast message
        data = websocket.receive_json()
        assert data["type"] == "USER_JOINED"
        assert data["user_id"] == str(user_id)


def test_websocket_broadcast(client: TestClient) -> None:
    project_id = uuid4()
    user1 = uuid4()
    user2 = uuid4()

    with client.websocket_connect(f"/ws/projects/{project_id}?user_id={user1}") as ws1:
        # ws1 receives own join message
        data = ws1.receive_json()
        assert data["type"] == "USER_JOINED"
        assert data["user_id"] == str(user1)

        with client.websocket_connect(f"/ws/projects/{project_id}?user_id={user2}") as ws2:
            # ws2 receives own join message
            data = ws2.receive_json()
            assert data["type"] == "USER_JOINED"
            assert data["user_id"] == str(user2)

            # ws1 should also receive user2 join message
            data = ws1.receive_json()
            assert data["type"] == "USER_JOINED"
            assert data["user_id"] == str(user2)

        # After ws2 disconnects, ws1 should receive USER_LEFT
        data = ws1.receive_json()
        assert data["type"] == "USER_LEFT"
        assert data["user_id"] == str(user2)


def test_websocket_generic_error(client: TestClient) -> None:
    project_id = uuid4()
    user_id = uuid4()

    # Patch broadcast to raise an exception
    with patch("coreason_foundry.api.websockets.ConnectionManager.broadcast", side_effect=Exception("Boom")):
        # The exception in 'finally' block (broadcast USER_LEFT) will bubble up
        with pytest.raises(Exception, match="Boom"):
            with client.websocket_connect(f"/ws/projects/{project_id}?user_id={user_id}"):
                pass
