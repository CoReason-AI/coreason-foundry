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

from coreason_foundry.managers import InMemoryProjectRepository, ProjectManager


@pytest.mark.asyncio
async def test_create_duplicate_names() -> None:
    """
    Complex Scenario: Two projects with the exact same name should be distinct entities
    with different IDs.
    """
    repo = InMemoryProjectRepository()
    manager = ProjectManager(repo)

    name = "Twin Agent"
    p1 = await manager.create_project(name)
    p2 = await manager.create_project(name)

    assert p1.name == name
    assert p2.name == name
    assert p1.id != p2.id
    assert p1 != p2  # Pydantic equality checks all fields, and IDs are different

    all_projects = await manager.list_projects()
    assert len(all_projects) == 2
    assert p1 in all_projects
    assert p2 in all_projects


@pytest.mark.asyncio
async def test_create_empty_name() -> None:
    """
    Edge Case: Creating a project with an empty string as a name.
    While not ideal for UI, the backend should handle it gracefully without crashing.
    """
    repo = InMemoryProjectRepository()
    manager = ProjectManager(repo)

    p = await manager.create_project("")
    assert p.name == ""
    assert p.id is not None


@pytest.mark.asyncio
async def test_create_whitespace_name() -> None:
    """
    Edge Case: Creating a project with whitespace-only name.
    """
    repo = InMemoryProjectRepository()
    manager = ProjectManager(repo)

    name = "   "
    p = await manager.create_project(name)
    assert p.name == name


@pytest.mark.asyncio
async def test_workflow_state_update() -> None:
    """
    Complex Scenario: Simulate a workflow where a project's state evolves.
    1. Create Project.
    2. Simulate a 'Draft Created' event by updating current_draft_id.
    3. Persist the change.
    4. Retrieve and verify.
    """
    repo = InMemoryProjectRepository()
    manager = ProjectManager(repo)

    # 1. Create
    project = await manager.create_project("Evolution Agent")
    original_id = project.id

    # 2. Update State (Simulating an external process updating the model)
    new_draft_id = uuid4()
    project.current_draft_id = new_draft_id

    # 3. Persist (Explicitly saving via repo, as manager update method doesn't exist yet)
    # Note: With InMemoryRepo, the object might be shared reference, but we call save to be explicit
    # about the intent of "persisting" changes in a real DB scenario.
    await repo.save(project)

    # 4. Retrieve fresh instance (conceptually)
    # In a real DB, we would refetch. Here we fetch via manager.
    retrieved = await manager.get_project(original_id)

    assert retrieved is not None
    assert retrieved.current_draft_id == new_draft_id
    assert retrieved.name == "Evolution Agent"
