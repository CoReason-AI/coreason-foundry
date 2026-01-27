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

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect

from coreason_foundry.api.dependencies import get_connection_manager, get_presence_registry
from coreason_foundry.api.websockets import ConnectionManager
from coreason_foundry.interfaces import PresenceRegistry
from coreason_foundry.utils.logger import logger

router = APIRouter()


@router.websocket("/ws/projects/{project_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    project_id: UUID,
    manager: Annotated[ConnectionManager, Depends(get_connection_manager)],
    presence: Annotated[PresenceRegistry, Depends(get_presence_registry)],
    user_id: Annotated[UUID, Query()],
) -> None:
    """
    WebSocket endpoint for real-time collaboration.
    """
    await manager.connect(project_id, websocket)
    await presence.add_user(project_id, user_id)

    try:
        await manager.broadcast(
            project_id,
            {"type": "USER_JOINED", "user_id": str(user_id)}
        )

        while True:
            # Keep connection alive and listen for messages
            await websocket.receive_text()
    except WebSocketDisconnect:
        logger.debug(f"User {user_id} disconnected from project {project_id}")
    except Exception as e:
        logger.warning(f"WebSocket error for user {user_id} in project {project_id}: {e}")
    finally:
        await presence.remove_user(project_id, user_id)
        manager.disconnect(project_id, websocket)
        await manager.broadcast(
            project_id,
            {"type": "USER_LEFT", "user_id": str(user_id)}
        )
