# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_foundry

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, status

from coreason_foundry.api.dependencies import get_connection_manager
from coreason_foundry.api.websockets import ConnectionManager

router = APIRouter(prefix="/ws/projects", tags=["websockets"])


@router.websocket("/{project_id}")
async def project_websocket(
    websocket: WebSocket,
    project_id: UUID,
    manager: Annotated[ConnectionManager, Depends(get_connection_manager)],
) -> None:
    """
    WebSocket endpoint for project real-time collaboration.
    Requires 'user_id' query parameter for authentication.
    """
    # 1. Authenticate (Simulated)
    user_id_str = websocket.query_params.get("user_id")
    if not user_id_str:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Missing user_id")
        return

    try:
        user_id = UUID(user_id_str)
    except ValueError:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid user_id")
        return

    try:
        # 2. Connect
        await manager.connect(websocket, project_id, user_id)

        # 3. Message Loop
        while True:
            # We expect simple JSON text messages, though we primarily send OUTbound.
            # In future iterations, we might handle inbound messages here.
            # For now, just keep the connection alive.
            await websocket.receive_text()
    except WebSocketDisconnect:
        # 4. Disconnect (Handle unexpected or expected disconnects)
        await manager.disconnect(websocket, project_id, user_id)
    except Exception:
        # Catch other errors to ensure cleanup
        await manager.disconnect(websocket, project_id, user_id)
