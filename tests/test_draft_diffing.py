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
from coreason_foundry.managers import DraftManager
from coreason_foundry.memory import InMemoryUnitOfWork
from coreason_foundry.models import Project


@pytest.fixture
def draft_manager() -> DraftManager:
    uow = InMemoryUnitOfWork()
    return DraftManager(uow)


@pytest.mark.asyncio
async def test_compare_versions_success(draft_manager: DraftManager) -> None:
    # Setup
    author_id = uuid4()
    project = Project(name="Test Project")
    await draft_manager.project_repo.add(project)

    draft1 = await draft_manager.create_draft(project.id, "Hello World\nLine 2", {}, author_id)

    draft2 = await draft_manager.create_draft(project.id, "Hello World\nLine 2 Modified", {}, author_id)

    # Execute
    diff = await draft_manager.compare_versions(draft1.id, draft2.id)

    # Verify
    assert "--- Draft v1" in diff
    assert "+++ Draft v2" in diff
    assert "-Line 2" in diff
    assert "+Line 2 Modified" in diff


@pytest.mark.asyncio
async def test_compare_versions_identical(draft_manager: DraftManager) -> None:
    # Setup
    author_id = uuid4()
    project = Project(name="Test Project")
    await draft_manager.project_repo.add(project)

    draft1 = await draft_manager.create_draft(project.id, "Hello World", {}, author_id)

    draft2 = await draft_manager.create_draft(project.id, "Hello World", {}, author_id)

    # Execute
    diff = await draft_manager.compare_versions(draft1.id, draft2.id)

    # Verify
    assert diff == ""


@pytest.mark.asyncio
async def test_compare_versions_not_found(draft_manager: DraftManager) -> None:
    # Setup
    author_id = uuid4()
    project = Project(name="Test Project")
    await draft_manager.project_repo.add(project)
    draft1 = await draft_manager.create_draft(project.id, "Hello World", {}, author_id)

    # Execute & Verify
    with pytest.raises(ValueError, match="not found"):
        await draft_manager.compare_versions(draft1.id, uuid4())

    with pytest.raises(ValueError, match="not found"):
        await draft_manager.compare_versions(uuid4(), draft1.id)


@pytest.mark.asyncio
async def test_compare_versions_different_projects(draft_manager: DraftManager) -> None:
    # Setup
    author_id = uuid4()
    project1 = Project(name="Project 1")
    await draft_manager.project_repo.add(project1)
    project2 = Project(name="Project 2")
    await draft_manager.project_repo.add(project2)

    draft1 = await draft_manager.create_draft(project1.id, "Content 1", {}, author_id)

    draft2 = await draft_manager.create_draft(project2.id, "Content 2", {}, author_id)

    # Execute & Verify
    with pytest.raises(ValueError, match="Cannot compare drafts from different projects"):
        await draft_manager.compare_versions(draft1.id, draft2.id)
