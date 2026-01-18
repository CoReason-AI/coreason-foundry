# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_foundry

from typing import AsyncGenerator
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from coreason_foundry.db.base import Base
from coreason_foundry.managers import ProjectManager
from coreason_foundry.models import Project
from coreason_foundry.repositories import SqlAlchemyProjectRepository

# Use sqlite+aiosqlite for in-memory testing of the SQLAlchemy repository
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(bind=engine, expire_on_commit=False)
    async with session_maker() as session:
        yield session

    await engine.dispose()


@pytest.mark.asyncio
async def test_sqlalchemy_repo_create_and_get(db_session: AsyncSession) -> None:
    repo = SqlAlchemyProjectRepository(db_session)
    project = Project(name="Integration Test Project")

    # Save
    saved_project = await repo.add(project)
    assert saved_project.id is not None
    assert saved_project.name == "Integration Test Project"

    # Get
    retrieved = await repo.get(project.id)
    assert retrieved is not None
    assert retrieved.id == project.id
    assert retrieved.name == project.name


@pytest.mark.asyncio
async def test_sqlalchemy_repo_get_not_found(db_session: AsyncSession) -> None:
    repo = SqlAlchemyProjectRepository(db_session)
    retrieved = await repo.get(uuid4())
    assert retrieved is None


@pytest.mark.asyncio
async def test_sqlalchemy_repo_list_all(db_session: AsyncSession) -> None:
    repo = SqlAlchemyProjectRepository(db_session)

    p1 = Project(name="Project A")
    p2 = Project(name="Project B")

    await repo.add(p1)
    await repo.add(p2)

    all_projects = await repo.list_all()
    assert len(all_projects) == 2
    # Check IDs explicitly
    ids = {p.id for p in all_projects}
    assert p1.id in ids
    assert p2.id in ids


@pytest.mark.asyncio
async def test_sqlalchemy_repo_update(db_session: AsyncSession) -> None:
    repo = SqlAlchemyProjectRepository(db_session)
    project = Project(name="Original Name")
    await repo.add(project)

    # Update object
    project.name = "Updated Name"
    new_draft_id = uuid4()
    project.current_draft_id = new_draft_id

    # Save again
    await repo.update(project)

    # Verify persistence
    retrieved = await repo.get(project.id)
    assert retrieved is not None
    assert retrieved.name == "Updated Name"
    assert retrieved.current_draft_id == new_draft_id


@pytest.mark.asyncio
async def test_manager_integration_with_sqlalchemy(db_session: AsyncSession) -> None:
    # Verify ProjectManager works with the real SQL repo
    repo = SqlAlchemyProjectRepository(db_session)
    manager = ProjectManager(repo)

    project = await manager.create_project("Managed Project")
    assert project.name == "Managed Project"

    retrieved = await manager.get_project(project.id)
    assert retrieved is not None
    assert retrieved.name == "Managed Project"
