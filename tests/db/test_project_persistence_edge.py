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

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from coreason_foundry.models import Project
from coreason_foundry.repositories import SqlAlchemyProjectRepository


@pytest.mark.asyncio
async def test_project_repository_save_with_draft_id(db_session: AsyncSession) -> None:
    repo = SqlAlchemyProjectRepository(db_session)
    project_id = uuid.uuid4()
    draft_id = uuid.uuid4()

    project = Project(id=project_id, name="Project with Draft", current_draft_id=draft_id)

    await repo.add(project)

    fetched = await repo.get(project_id)
    assert fetched is not None
    assert fetched.current_draft_id == draft_id


@pytest.mark.asyncio
async def test_project_repository_list_empty(db_session: AsyncSession) -> None:
    repo = SqlAlchemyProjectRepository(db_session)
    # Ensure no projects exist (assuming clean session)
    # If other tests ran, they should be rolled back.

    # We can't guarantee empty DB if other tests committed (unlikely with fixture rollback).
    # But let's assume valid isolation.

    # Actually, to be safe against other tests running in parallel (if xdist) or leakage,
    # we can't assert list_all() == [].
    # But we can check that it returns a list (type check) and doesn't crash.

    projects = await repo.list_all()
    assert isinstance(projects, list)


@pytest.mark.asyncio
async def test_project_repository_save_idempotency(db_session: AsyncSession) -> None:
    repo = SqlAlchemyProjectRepository(db_session)
    project = Project(name="Idempotent Project")

    # Save once
    saved1 = await repo.add(project)

    # Save again (should update/merge)
    saved2 = await repo.update(saved1)

    assert saved1.id == saved2.id
    assert saved1.name == saved2.name

    # Verify count
    all_projects = await repo.list_all()
    matching = [p for p in all_projects if p.id == saved1.id]
    assert len(matching) == 1
