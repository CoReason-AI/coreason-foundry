# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_foundry

from uuid import uuid4

import pytest

from coreason_foundry.exceptions import ProjectNotFoundError
from coreason_foundry.managers import DraftManager, ProjectManager
from coreason_foundry.memory import InMemoryUnitOfWork


@pytest.mark.asyncio
async def test_create_first_draft() -> None:
    uow = InMemoryUnitOfWork()
    project_repo = uow.projects

    project_manager = ProjectManager(project_repo)
    draft_manager = DraftManager(uow)

    # Create Project
    project = await project_manager.create_project("Agent Alpha")
    assert project.current_draft_id is None

    # Create Draft
    author_id = uuid4()
    draft = await draft_manager.create_draft(
        project_id=project.id,
        prompt_text="System prompt v1",
        model_configuration={"temperature": 0.7},
        author_id=author_id,
    )

    # Verify Draft
    assert draft.version_number == 1
    assert draft.project_id == project.id
    assert draft.prompt_text == "System prompt v1"
    assert draft.author_id == author_id

    # Verify Project Update
    updated_project = await project_manager.get_project(project.id)
    assert updated_project is not None
    assert updated_project.current_draft_id == draft.id


@pytest.mark.asyncio
async def test_create_subsequent_drafts() -> None:
    uow = InMemoryUnitOfWork()
    project_repo = uow.projects

    project_manager = ProjectManager(project_repo)
    draft_manager = DraftManager(uow)

    project = await project_manager.create_project("Agent Beta")
    author_id = uuid4()

    # Draft v1
    draft_v1 = await draft_manager.create_draft(
        project_id=project.id,
        prompt_text="v1",
        model_configuration={},
        author_id=author_id,
    )
    assert draft_v1.version_number == 1

    # Draft v2
    draft_v2 = await draft_manager.create_draft(
        project_id=project.id,
        prompt_text="v2",
        model_configuration={},
        author_id=author_id,
    )
    assert draft_v2.version_number == 2
    assert draft_v2.id != draft_v1.id

    # Verify Project Pointer points to v2
    updated_project = await project_manager.get_project(project.id)
    assert updated_project is not None
    assert updated_project.current_draft_id == draft_v2.id


@pytest.mark.asyncio
async def test_create_draft_project_not_found() -> None:
    uow = InMemoryUnitOfWork()
    draft_manager = DraftManager(uow)

    with pytest.raises(ProjectNotFoundError):
        await draft_manager.create_draft(
            project_id=uuid4(),
            prompt_text="Fail",
            model_configuration={},
            author_id=uuid4(),
        )


@pytest.mark.asyncio
async def test_in_memory_draft_repo_get() -> None:
    """Test get method of InMemoryDraftRepository to reach 100% coverage."""
    uow = InMemoryUnitOfWork()
    project_repo = uow.projects
    draft_repo = uow.drafts

    draft_manager = DraftManager(uow)
    project_manager = ProjectManager(project_repo)

    project = await project_manager.create_project("Test Agent")
    draft = await draft_manager.create_draft(
        project_id=project.id,
        prompt_text="Prompt",
        model_configuration={},
        author_id=uuid4(),
    )

    retrieved = await draft_repo.get(draft.id)
    assert retrieved == draft

    assert await draft_repo.get(uuid4()) is None
