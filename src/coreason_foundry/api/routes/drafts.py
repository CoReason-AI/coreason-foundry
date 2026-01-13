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

from fastapi import APIRouter, Depends, HTTPException, Query, status

from coreason_foundry.api.dependencies import get_current_user_id, get_draft_manager
from coreason_foundry.api.schemas import DraftCreate, DraftDiff, DraftRead
from coreason_foundry.exceptions import ProjectNotFoundError
from coreason_foundry.managers import DraftManager

router = APIRouter(tags=["drafts"])


@router.post("/projects/{project_id}/drafts", response_model=DraftRead, status_code=status.HTTP_201_CREATED)
async def create_draft(
    project_id: UUID,
    draft_in: DraftCreate,
    manager: Annotated[DraftManager, Depends(get_draft_manager)],
    user_id: Annotated[UUID, Depends(get_current_user_id)],
) -> DraftRead:
    """
    Create a new immutable draft version for a project.
    """
    try:
        draft = await manager.create_draft(
            project_id=project_id,
            prompt_text=draft_in.prompt_text,
            model_configuration=draft_in.model_configuration,
            author_id=user_id,
            scratchpad=draft_in.scratchpad,
        )
        return DraftRead(
            id=draft.id,
            project_id=draft.project_id,
            version_number=draft.version_number,
            prompt_text=draft.prompt_text,
            model_configuration=draft.model_configuration,
            scratchpad=draft.scratchpad,
            author_id=draft.author_id,
            created_at=draft.created_at,
        )
    except ProjectNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found") from None


@router.get("/projects/{project_id}/drafts", response_model=List[DraftRead])
async def list_drafts(
    project_id: UUID,
    manager: Annotated[DraftManager, Depends(get_draft_manager)],
) -> List[DraftRead]:
    """
    List all drafts for a given project, ordered by version number.
    """
    drafts = await manager.draft_repo.list_by_project(project_id)
    return [
        DraftRead(
            id=d.id,
            project_id=d.project_id,
            version_number=d.version_number,
            prompt_text=d.prompt_text,
            model_configuration=d.model_configuration,
            scratchpad=d.scratchpad,
            author_id=d.author_id,
            created_at=d.created_at,
        )
        for d in drafts
    ]


@router.get("/drafts/compare", response_model=DraftDiff)
async def compare_drafts(
    manager: Annotated[DraftManager, Depends(get_draft_manager)],
    base_id: UUID = Query(..., description="The ID of the base draft"),
    target_id: UUID = Query(..., description="The ID of the target draft"),
) -> DraftDiff:
    """
    Compare two drafts and return the unified diff of their prompt text.
    """
    try:
        diff = await manager.compare_versions(base_id, target_id)
        return DraftDiff(diff=diff)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.get("/drafts/{draft_id}", response_model=DraftRead)
async def get_draft(
    draft_id: UUID,
    manager: Annotated[DraftManager, Depends(get_draft_manager)],
) -> DraftRead:
    """
    Get a specific draft by ID.
    """
    draft = await manager.draft_repo.get(draft_id)
    if not draft:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Draft not found") from None

    return DraftRead(
        id=draft.id,
        project_id=draft.project_id,
        version_number=draft.version_number,
        prompt_text=draft.prompt_text,
        model_configuration=draft.model_configuration,
        scratchpad=draft.scratchpad,
        author_id=draft.author_id,
        created_at=draft.created_at,
    )
