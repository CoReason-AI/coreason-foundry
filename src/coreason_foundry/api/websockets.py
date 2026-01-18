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

from fastapi import WebSocket

from coreason_foundry.managers import LockRegistry, PresenceRegistry
from coreason_foundry.utils.logger import logger


class ConnectionManager:
    """
    Manages active WebSocket connections and integrates with the PresenceRegistry.
    """

    def __init__(self, presence_registry: PresenceRegistry, lock_registry: LockRegistry) -> None:
        self.presence_registry = presence_registry
        self.lock_registry = lock_registry
        # Map project_id -> list of active WebSockets
        self.active_connections: Dict[UUID, List[WebSocket]] = defaultdict(list)

    async def connect(self, websocket: WebSocket, project_id: UUID, user_id: UUID) -> None:
        """
        Accepts a WebSocket connection and registers the user's presence.
        """
        await websocket.accept()
        self.active_connections[project_id].append(websocket)
        await self.presence_registry.add_user(project_id, user_id)
        logger.info(f"WebSocket connected: User {user_id} in Project {project_id}")

        # Notify others of user joining
        try:
            await self.broadcast(
                project_id,
                {
                    "type": "USER_JOINED",
                    "payload": {"user_id": str(user_id)},
                },
            )
        except Exception as e:
            logger.error(f"Failed to broadcast USER_JOINED for {user_id}: {e}")
            # Do not fail the connection if broadcast fails

    async def disconnect(self, websocket: WebSocket, project_id: UUID, user_id: UUID) -> None:
        """
        Removes a WebSocket connection and updates presence.
        """
        if websocket in self.active_connections[project_id]:
            self.active_connections[project_id].remove(websocket)

        await self.presence_registry.remove_user(project_id, user_id)
        logger.info(f"WebSocket disconnected: User {user_id} in Project {project_id}")

        # Notify others of user leaving
        try:
            await self.broadcast(
                project_id,
                {
                    "type": "USER_LEFT",
                    "payload": {"user_id": str(user_id)},
                },
            )
        except Exception as e:
            logger.error(f"Failed to broadcast USER_LEFT for {user_id}: {e}")

        # Release locks held by this user.
        try:
            released_count = await self.lock_registry.release_all_for_user(project_id, user_id)
            if released_count > 0:
                logger.info(f"Released {released_count} locks for User {user_id} in Project {project_id}")
        except Exception as e:
            logger.error(f"Failed to release locks for user {user_id}: {e}")

    async def broadcast(self, project_id: UUID, message: Dict[str, Any]) -> None:
        """
        Broadcasts a JSON message to all connected clients in a project.
        """
        # We iterate over a copy in case connections drop during iteration
        for connection in list(self.active_connections[project_id]):
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Failed to send broadcast message: {e}")
                # We assume the route handler deals with disconnects, but if send fails here,
                # it might be a zombie connection. We leave cleanup to the main loop or disconnect handler.
