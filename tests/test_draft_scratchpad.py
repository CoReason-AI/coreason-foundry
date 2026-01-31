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

from coreason_foundry.managers import DraftManager, ProjectManager
from coreason_foundry.memory import InMemoryUnitOfWork


@pytest.mark.asyncio
async def test_create_draft_with_scratchpad() -> None:
    # Setup
    uow = InMemoryUnitOfWork()
    manager = DraftManager(uow)
    project_manager = ProjectManager(uow.projects)

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
    retrieved_draft = await uow.drafts.get(draft.id)
    assert retrieved_draft is not None
    assert retrieved_draft.scratchpad == scratchpad_content


@pytest.mark.asyncio
async def test_create_draft_without_scratchpad() -> None:
    # Setup
    uow = InMemoryUnitOfWork()
    manager = DraftManager(uow)
    project_manager = ProjectManager(uow.projects)

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
    retrieved_draft = await uow.drafts.get(draft.id)
    retrieved_draft = await uow.drafts.get(draft.id)
    assert retrieved_draft is not None
    assert retrieved_draft.scratchpad is None
