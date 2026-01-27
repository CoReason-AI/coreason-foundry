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
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

from coreason_foundry.api.websockets import ConnectionManager


@pytest.mark.asyncio
async def test_connection_manager_connect():
    manager = ConnectionManager()
    project_id = uuid4()
    mock_ws = AsyncMock()

    await manager.connect(project_id, mock_ws)

    mock_ws.accept.assert_called_once()
    assert mock_ws in manager.active_connections[project_id]


@pytest.mark.asyncio
async def test_connection_manager_disconnect():
    manager = ConnectionManager()
    project_id = uuid4()
    mock_ws = AsyncMock()

    # Manually add to simulate connection
    manager.active_connections[project_id].append(mock_ws)

    manager.disconnect(project_id, mock_ws)

    # Check if empty list is cleaned up
    # Note: We must be careful not to access manager.active_connections[project_id]
    # as it would recreate the entry in the defaultdict.
    assert project_id not in manager.active_connections


@pytest.mark.asyncio
async def test_connection_manager_broadcast():
    manager = ConnectionManager()
    project_id = uuid4()
    mock_ws1 = AsyncMock()
    mock_ws2 = AsyncMock()

    manager.active_connections[project_id].extend([mock_ws1, mock_ws2])

    message = {"type": "TEST_MESSAGE"}
    await manager.broadcast(project_id, message)

    mock_ws1.send_json.assert_called_with(message)
    mock_ws2.send_json.assert_called_with(message)


@pytest.mark.asyncio
async def test_connection_manager_broadcast_error_handling():
    manager = ConnectionManager()
    project_id = uuid4()
    mock_ws = AsyncMock()
    mock_ws.send_json.side_effect = Exception("Connection lost")

    manager.active_connections[project_id].append(mock_ws)

    # Should not raise exception
    await manager.broadcast(project_id, {"msg": "test"})

    mock_ws.send_json.assert_called_once()
    # Verify connection was removed
    assert mock_ws not in manager.active_connections.get(project_id, [])
