# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_foundry

from collections import defaultdict
from typing import Any, Dict, List
from uuid import UUID

from coreason_foundry.utils.logger import logger
from starlette.websockets import WebSocket


class ConnectionManager:
    """
    Manages active WebSocket connections grouped by project_id.

    This manager handles:
    - Connecting sockets and mapping them to projects.
    - Disconnecting sockets and cleaning up empty project groups.
    - Broadcasting messages to all sockets in a project.
    """

    def __init__(self) -> None:
        self.active_connections: Dict[UUID, List[WebSocket]] = defaultdict(list)

    async def connect(self, project_id: UUID, websocket: WebSocket) -> None:
        """
        Accepts the connection and stores the reference.
        """
        await websocket.accept()
        self.active_connections[project_id].append(websocket)
        logger.debug(f"WebSocket connected to project {project_id}")

    def disconnect(self, project_id: UUID, websocket: WebSocket) -> None:
        """
        Removes the connection reference.
        """
        if project_id in self.active_connections:
            if websocket in self.active_connections[project_id]:
                self.active_connections[project_id].remove(websocket)
                logger.debug(f"WebSocket disconnected from project {project_id}")

            # Check if list is empty
            if len(self.active_connections[project_id]) == 0:
                del self.active_connections[project_id]

    async def broadcast(self, project_id: UUID, message: Dict[str, Any]) -> None:
        """
        Sends a JSON message to all active sockets in the project group.
        """
        if project_id in self.active_connections:
            # Iterate over a copy of the list to safely modify it if needed
            for connection in self.active_connections[project_id][:]:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.warning(f"Failed to send message to socket in project {project_id}: {e}")
                    self.disconnect(project_id, connection)
