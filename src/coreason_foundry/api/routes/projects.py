# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_foundry

from typing import Annotated, List
from uuid import UUID

from coreason_foundry.api.dependencies import get_project_manager
from coreason_foundry.api.schemas import ProjectCreate
from coreason_foundry.managers import ProjectManager
from coreason_foundry.models import Project
from fastapi import APIRouter, Depends, HTTPException, status

router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("/", response_model=Project, status_code=status.HTTP_201_CREATED)
async def create_project(
    project_in: ProjectCreate,
    manager: Annotated[ProjectManager, Depends(get_project_manager)],
) -> Project:
    """
    Create a new project.
    """
    return await manager.create_project(name=project_in.name)


@router.get("/", response_model=List[Project])
async def list_projects(
    manager: Annotated[ProjectManager, Depends(get_project_manager)],
) -> List[Project]:
    """
    List all projects.
    """
    return await manager.list_projects()


@router.get("/{project_id}", response_model=Project)
async def get_project(
    project_id: UUID,
    manager: Annotated[ProjectManager, Depends(get_project_manager)],
) -> Project:
    """
    Get a project by ID.
    """
    project = await manager.get_project(project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project
