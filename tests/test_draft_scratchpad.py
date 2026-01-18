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

from coreason_foundry.managers import DraftManager, InMemoryDraftRepository, InMemoryProjectRepository, ProjectManager


@pytest.mark.asyncio
async def test_create_draft_with_scratchpad() -> None:
    # Setup
    project_repo = InMemoryProjectRepository()
    draft_repo = InMemoryDraftRepository()
    manager = DraftManager(project_repo, draft_repo)
    project_manager = ProjectManager(project_repo)

    project = await project_manager.create_project("Test Project")
    author_id = uuid4()

    # Test creating draft with scratchpad
    scratchpad_content = "To-Do: Fix JSON schema\n- [ ] Task 1"
    draft = await manager.create_draft(
        project_id=project.id,
        prompt_text="System Prompt",
        model_configuration={"temp": 0.7},
        author_id=author_id,
        scratchpad=scratchpad_content,
    )

    # Verify
    assert draft.scratchpad == scratchpad_content
    assert draft.version_number == 1

    # Verify retrieval
    retrieved_draft = await draft_repo.get(draft.id)
    assert retrieved_draft is not None
    assert retrieved_draft.scratchpad == scratchpad_content


@pytest.mark.asyncio
async def test_create_draft_without_scratchpad() -> None:
    # Setup
    project_repo = InMemoryProjectRepository()
    draft_repo = InMemoryDraftRepository()
    manager = DraftManager(project_repo, draft_repo)
    project_manager = ProjectManager(project_repo)

    project = await project_manager.create_project("Test Project")
    author_id = uuid4()

    # Test creating draft without scratchpad (default None)
    draft = await manager.create_draft(
        project_id=project.id, prompt_text="System Prompt", model_configuration={"temp": 0.7}, author_id=author_id
    )

    # Verify
    assert draft.scratchpad is None
    assert draft.version_number == 1

    # Verify retrieval
    retrieved_draft = await draft_repo.get(draft.id)
    assert retrieved_draft is not None
    assert retrieved_draft.scratchpad is None
