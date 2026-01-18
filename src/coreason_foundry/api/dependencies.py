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

from coreason_foundry.interfaces import DraftRepository, ProjectRepository, UnitOfWork
from coreason_foundry.managers import (
    DraftManager,
    ProjectManager,
)
from coreason_foundry.memory import (
    InMemoryUnitOfWork,
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
def get_unit_of_work() -> UnitOfWork:
    """
    Returns a singleton InMemoryUnitOfWork for testing.
    In production with SQL, this would not be cached/singleton, but request-scoped.
    """
    return InMemoryUnitOfWork()


def get_project_repository(
    uow: Annotated[UnitOfWork, Depends(get_unit_of_work)],
) -> ProjectRepository:
    """
    Returns the ProjectRepository from the UnitOfWork.
    """
    return uow.projects


def get_draft_repository(
    uow: Annotated[UnitOfWork, Depends(get_unit_of_work)],
) -> DraftRepository:
    """
    Returns the DraftRepository from the UnitOfWork.
    """
    return uow.drafts


def get_project_manager(
    repository: Annotated[ProjectRepository, Depends(get_project_repository)],
) -> ProjectManager:
    """
    Returns a ProjectManager instance with the injected repository.
    """
    return ProjectManager(repository=repository)


def get_draft_manager(
    uow: Annotated[UnitOfWork, Depends(get_unit_of_work)],
) -> DraftManager:
    """
    Returns a DraftManager instance with injected UnitOfWork.
    """
    return DraftManager(uow=uow)
