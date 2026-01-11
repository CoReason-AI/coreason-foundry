# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_foundry

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from coreason_foundry.models import Project
from coreason_foundry.repositories import SqlAlchemyProjectRepository


@pytest.mark.asyncio
async def test_project_repository_save_and_get(db_session: AsyncSession) -> None:
    repo = SqlAlchemyProjectRepository(db_session)
    project_id = uuid.uuid4()

    project = Project(
        id=project_id,
        name="Test Project",
        created_at=datetime.now(timezone.utc),
    )

    # Save
    saved_project = await repo.save(project)
    assert saved_project.id == project_id
    assert saved_project.name == "Test Project"
    assert saved_project.created_at == project.created_at

    # Get
    fetched_project = await repo.get(project_id)
    assert fetched_project is not None
    assert fetched_project.id == project_id
    assert fetched_project.name == "Test Project"

    # Handle SQLite timezone stripping in tests
    fetched_created_at = fetched_project.created_at
    if fetched_created_at.tzinfo is None:
        fetched_created_at = fetched_created_at.replace(tzinfo=timezone.utc)

    assert fetched_created_at == project.created_at


@pytest.mark.asyncio
async def test_project_repository_update(db_session: AsyncSession) -> None:
    repo = SqlAlchemyProjectRepository(db_session)
    project_id = uuid.uuid4()

    project = Project(
        id=project_id,
        name="Test Project",
    )
    await repo.save(project)

    # Update
    project.name = "Updated Project Name"
    updated_project = await repo.save(project)
    assert updated_project.name == "Updated Project Name"

    # Verify Get
    fetched_project = await repo.get(project_id)
    assert fetched_project is not None
    assert fetched_project.name == "Updated Project Name"


@pytest.mark.asyncio
async def test_project_repository_get_non_existent(db_session: AsyncSession) -> None:
    repo = SqlAlchemyProjectRepository(db_session)
    fetched_project = await repo.get(uuid.uuid4())
    assert fetched_project is None


@pytest.mark.asyncio
async def test_project_repository_list_all(db_session: AsyncSession) -> None:
    repo = SqlAlchemyProjectRepository(db_session)

    # Empty initially (assuming test isolation, but fixture might keep state if not careful?
    # Usually db_session fixture in these setups handles transaction rollback or creates new DB)
    # Let's see what happens.

    # Create projects
    project1 = Project(id=uuid.uuid4(), name="Project A")
    project2 = Project(id=uuid.uuid4(), name="Project B")

    await repo.save(project1)
    await repo.save(project2)

    projects = await repo.list_all()
    # We might have other projects from other tests if the DB is shared/not cleaned.
    # But usually sqlite :memory: is per test or transaction rollback is used.
    # The fixture logic I recalled said it uses rollback.

    # Filter by IDs we just created to be safe
    created_ids = {project1.id, project2.id}
    found_projects = [p for p in projects if p.id in created_ids]

    assert len(found_projects) == 2
    names = {p.name for p in found_projects}
    assert "Project A" in names
    assert "Project B" in names
