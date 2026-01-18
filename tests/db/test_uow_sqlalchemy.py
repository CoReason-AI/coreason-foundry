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
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from coreason_foundry.db.models import ProjectORM
from coreason_foundry.models import Project
from coreason_foundry.repositories import SqlAlchemyUnitOfWork


@pytest.mark.asyncio
async def test_sqlalchemy_uow_commit(db_session: AsyncSession) -> None:
    uow = SqlAlchemyUnitOfWork(db_session)
    project_id = uuid.uuid4()
    project = Project(id=project_id, name="UoW Commit Test")

    async with uow:
        await uow.projects.add(project)
        # Auto-commit on exit

    # Verify persistence in DB
    result = await db_session.execute(select(ProjectORM).where(ProjectORM.id == project_id))
    persisted = result.scalar_one_or_none()
    assert persisted is not None
    assert persisted.name == "UoW Commit Test"


@pytest.mark.asyncio
async def test_sqlalchemy_uow_rollback_on_error(db_session: AsyncSession) -> None:
    uow = SqlAlchemyUnitOfWork(db_session)
    project_id = uuid.uuid4()
    project = Project(id=project_id, name="UoW Rollback Test")

    with pytest.raises(RuntimeError):
        async with uow:
            await uow.projects.add(project)
            raise RuntimeError("Force Rollback")

    # Verify NOT persisted
    result = await db_session.execute(select(ProjectORM).where(ProjectORM.id == project_id))
    persisted = result.scalar_one_or_none()
    assert persisted is None


@pytest.mark.asyncio
async def test_sqlalchemy_uow_manual_rollback(db_session: AsyncSession) -> None:
    uow = SqlAlchemyUnitOfWork(db_session)
    project_id = uuid.uuid4()
    project = Project(id=project_id, name="Manual Rollback")

    async with uow:
        await uow.projects.add(project)
        await uow.rollback()
        # Even though we called rollback, the context manager will try to commit on exit?
        # Let's check implementation.
        # __aexit__: if exc_type: rollback else: commit.
        # If we manually rollback, the session is rolled back.
        # Then commit() is called on empty/rolled back transaction.
        # SQLAlchemy handles commit on inactive transaction gracefully or starts new?
        # Usually it's fine.

        # However, to be strictly correct, if we rollback manually, we might want to avoid the auto-commit.
        # But for this test, we want to ensure rollback worked.

    # Verify NOT persisted
    result = await db_session.execute(select(ProjectORM).where(ProjectORM.id == project_id))
    persisted = result.scalar_one_or_none()
    assert persisted is None
