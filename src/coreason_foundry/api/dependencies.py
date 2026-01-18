# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_foundry

from functools import lru_cache
from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header, HTTPException, status
from redis.asyncio import Redis

from coreason_foundry.api.websockets import ConnectionManager
from coreason_foundry.locking import RedisLockRegistry
from coreason_foundry.managers import (
    DraftManager,
    DraftRepository,
    InMemoryDraftRepository,
    InMemoryPresenceRegistry,
    InMemoryProjectRepository,
    LockRegistry,
    PresenceRegistry,
    ProjectManager,
    ProjectRepository,
)


def get_current_user_id(x_user_id: Annotated[str | None, Header()] = None) -> UUID:
    """
    Simulates authentication by extracting the User ID from the X-User-ID header.
    In a real scenario, this would validate a JWT token.
    """
    if not x_user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-User-ID header",
        )
    try:
        return UUID(x_user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid X-User-ID format (must be UUID)",
        ) from None


@lru_cache
def get_project_repository() -> ProjectRepository:
    """
    Returns a singleton instance of the ProjectRepository.
    Defaults to InMemoryProjectRepository for this iteration.
    """
    return InMemoryProjectRepository()


@lru_cache
def get_draft_repository() -> DraftRepository:
    """
    Returns a singleton instance of the DraftRepository.
    Defaults to InMemoryDraftRepository for this iteration.
    """
    return InMemoryDraftRepository()


@lru_cache
def get_presence_registry() -> PresenceRegistry:
    """
    Returns a singleton instance of the PresenceRegistry.
    Defaults to InMemoryPresenceRegistry for this iteration.
    """
    return InMemoryPresenceRegistry()


def get_redis_client() -> Redis:
    """
    Returns a Redis client.
    Assuming localhost for now, or use environment variables in future.
    """
    # Using decode_responses=False to match existing code logic where we decode manually
    return Redis(host="localhost", port=6379, db=0)


@lru_cache
def get_lock_registry(
    redis_client: Annotated[Redis, Depends(get_redis_client)],
) -> LockRegistry:
    """
    Returns a singleton instance of the LockRegistry.
    """
    return RedisLockRegistry(redis_client=redis_client)


@lru_cache
def get_connection_manager(
    presence_registry: Annotated[PresenceRegistry, Depends(get_presence_registry)],
    lock_registry: Annotated[LockRegistry, Depends(get_lock_registry)],
) -> ConnectionManager:
    """
    Returns a singleton instance of the ConnectionManager.
    """
    return ConnectionManager(presence_registry=presence_registry, lock_registry=lock_registry)


def get_project_manager(
    repository: Annotated[ProjectRepository, Depends(get_project_repository)],
) -> ProjectManager:
    """
    Returns a ProjectManager instance with the injected repository.
    """
    return ProjectManager(repository=repository)


def get_draft_manager(
    project_repo: Annotated[ProjectRepository, Depends(get_project_repository)],
    draft_repo: Annotated[DraftRepository, Depends(get_draft_repository)],
) -> DraftManager:
    """
    Returns a DraftManager instance with injected repositories.
    """
    return DraftManager(project_repo=project_repo, draft_repo=draft_repo)
