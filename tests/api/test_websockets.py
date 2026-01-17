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
from typing import Any, Generator, Tuple
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from coreason_foundry.api.app import app
from coreason_foundry.api.dependencies import get_connection_manager, get_presence_registry
from coreason_foundry.api.websockets import ConnectionManager
from coreason_foundry.managers import InMemoryPresenceRegistry, PresenceRegistry


@pytest.fixture
def fresh_deps() -> Generator[Tuple[PresenceRegistry, ConnectionManager], None, None]:
    """
    Overrides dependencies with fresh instances for each test.
    """
    registry = InMemoryPresenceRegistry()
    manager = ConnectionManager(registry)

    def override_get_presence_registry() -> PresenceRegistry:
        return registry

    def override_get_connection_manager() -> ConnectionManager:
        return manager

    app.dependency_overrides[get_presence_registry] = override_get_presence_registry
    app.dependency_overrides[get_connection_manager] = override_get_connection_manager

    yield registry, manager

    app.dependency_overrides = {}


@pytest.fixture
def client(fresh_deps: Tuple[PresenceRegistry, ConnectionManager]) -> TestClient:
    return TestClient(app)


def test_websocket_connect_success(client: TestClient) -> None:
    project_id = uuid4()
    user_id = uuid4()

    try:
        with client.websocket_connect(f"/ws/projects/{project_id}?user_id={user_id}") as websocket:
            data = websocket.receive_json()
            assert data["type"] == "USER_JOINED"
            assert data["payload"]["user_id"] == str(user_id)
            websocket.close()
    except WebSocketDisconnect as e:
        assert e.code == 1000


def test_websocket_connect_missing_user_id(client: TestClient) -> None:
    project_id = uuid4()
    with pytest.raises(WebSocketDisconnect) as exc:
        with client.websocket_connect(f"/ws/projects/{project_id}"):
            pass
    assert exc.value.code in [1000, 1008]


def test_websocket_connect_invalid_user_id(client: TestClient) -> None:
    project_id = uuid4()
    with pytest.raises(WebSocketDisconnect) as exc:
        with client.websocket_connect(f"/ws/projects/{project_id}?user_id=invalid"):
            pass
    assert exc.value.code in [1000, 1008]


@pytest.mark.asyncio
async def test_presence_update_on_connect_disconnect(fresh_deps: Tuple[PresenceRegistry, ConnectionManager]) -> None:
    # Retrieve the fresh registry instance used by the app
    registry, _ = fresh_deps

    client = TestClient(app)
    project_id = uuid4()
    user_id = uuid4()

    # Initial state
    users = await registry.get_present_users(project_id)
    assert user_id not in users

    try:
        with client.websocket_connect(f"/ws/projects/{project_id}?user_id={user_id}") as ws:
            # Connected
            users = await registry.get_present_users(project_id)
            assert user_id in users
            ws.close()
    except WebSocketDisconnect as e:
        assert e.code == 1000

    # Disconnected
    users = await registry.get_present_users(project_id)
    assert user_id not in users


def test_broadcast_to_multiple_clients(client: TestClient) -> None:
    project_id = uuid4()
    user1 = uuid4()
    user2 = uuid4()

    try:
        with client.websocket_connect(f"/ws/projects/{project_id}?user_id={user1}") as ws1:
            msg1 = ws1.receive_json()
            assert msg1["type"] == "USER_JOINED"
            assert msg1["payload"]["user_id"] == str(user1)

            with client.websocket_connect(f"/ws/projects/{project_id}?user_id={user2}") as ws2:
                msg2_own = ws2.receive_json()
                assert msg2_own["type"] == "USER_JOINED"
                assert msg2_own["payload"]["user_id"] == str(user2)

                msg1_notification = ws1.receive_json()
                assert msg1_notification["type"] == "USER_JOINED"
                assert msg1_notification["payload"]["user_id"] == str(user2)

                ws2.close()

            msg1_leave = ws1.receive_json()
            assert msg1_leave["type"] == "USER_LEFT"
            assert msg1_leave["payload"]["user_id"] == str(user2)

            ws1.close()
    except WebSocketDisconnect as e:
        assert e.code == 1000


@pytest.mark.asyncio
async def test_broadcast_exception_handling() -> None:
    """
    Test that an exception during broadcast (e.g. sending to a closed socket)
    is caught and logged, and doesn't crash the broadcaster.
    """

    class MockWebSocket:
        async def send_json(self, data: Any) -> None:
            raise Exception("Connection lost")

    registry = InMemoryPresenceRegistry()
    manager = ConnectionManager(registry)

    project_id = uuid4()
    mock_ws = MockWebSocket()

    manager.active_connections[project_id].append(mock_ws)

    # Should not raise exception
    await manager.broadcast(project_id, {"type": "TEST"})


def test_route_generic_exception_handling(fresh_deps: Tuple[PresenceRegistry, ConnectionManager]) -> None:
    """
    Test that a generic exception in the websocket loop triggers disconnect/cleanup.
    (Synchronous test version)
    """
    _, manager = fresh_deps
    project_id = uuid4()
    user_id = uuid4()

    # Use patch.object to safely mock methods on the instance
    # We use asyncio.Future to simulate async return values

    f_err: asyncio.Future[None] = asyncio.Future()
    f_err.set_exception(Exception("Something went wrong"))

    f_ok: asyncio.Future[None] = asyncio.Future()
    f_ok.set_result(None)

    # We need to track if disconnect was called.
    # MagicMock can track calls.

    mock_connect = MagicMock(return_value=f_err)
    mock_disconnect = MagicMock(return_value=f_ok)

    with patch.object(manager, "connect", mock_connect):
        with patch.object(manager, "disconnect", mock_disconnect):
            client = TestClient(app)
            try:
                with pytest.raises(WebSocketDisconnect):
                    with client.websocket_connect(f"/ws/projects/{project_id}?user_id={user_id}"):
                        pass
            except Exception:
                pass  # Should not happen if pytest.raises catches it

    assert mock_disconnect.called
