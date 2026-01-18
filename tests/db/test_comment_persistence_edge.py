# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_foundry

import asyncio
from typing import Any
from uuid import uuid4

import pytest
from sqlalchemy import event, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from coreason_foundry.db.base import Base
from coreason_foundry.db.models import DraftORM
from coreason_foundry.db.session import DatabaseSessionManager, DatabaseSettings
from coreason_foundry.models import Comment, Draft, Project
from coreason_foundry.repositories import (
    SqlAlchemyCommentRepository,
    SqlAlchemyDraftRepository,
    SqlAlchemyProjectRepository,
)


@pytest.mark.asyncio
async def test_orphan_comment_rejection(db_session: AsyncSession) -> None:
    """
    Verify that saving a comment for a non-existent draft raises an IntegrityError.
    This ensures foreign key constraints are active and enforced.
    """
    repo = SqlAlchemyCommentRepository(db_session)

    # Create a comment pointing to a random UUID (no such draft)
    orphan_comment = Comment(draft_id=uuid4(), target_field="prompt_text", text="I am an orphan", author_id=uuid4())

    with pytest.raises(IntegrityError):
        await repo.save(orphan_comment)


@pytest.mark.asyncio
async def test_referential_integrity_on_parent_delete(db_session: AsyncSession) -> None:
    """
    Verify that attempting to delete a Draft that has linked Comments raises an IntegrityError.
    This ensures that we don't accidentally leave orphaned comments (NO ACTION/RESTRICT behavior).
    """
    project_repo = SqlAlchemyProjectRepository(db_session)
    draft_repo = SqlAlchemyDraftRepository(db_session)
    comment_repo = SqlAlchemyCommentRepository(db_session)

    # 1. Create Hierarchy
    project = Project(name="Parent Project")
    await project_repo.save(project)

    draft = Draft(
        project_id=project.id, version_number=1, prompt_text="Base", model_configuration={}, author_id=uuid4()
    )
    await draft_repo.save(draft)

    comment = Comment(draft_id=draft.id, target_field="prompt_text", text="Child Comment", author_id=uuid4())
    await comment_repo.save(comment)

    # 2. Attempt to delete the Draft
    # Since DraftRepository doesn't expose delete, we do it via session/ORM directly for this test
    # to verify the DB constraint.

    # Fetch ORM object to delete
    stmt = select(DraftORM).where(DraftORM.id == draft.id)
    result = await db_session.execute(stmt)
    draft_orm = result.scalar_one()

    await db_session.delete(draft_orm)

    # 3. Verify IntegrityError on flush/commit
    with pytest.raises(IntegrityError):
        await db_session.flush()


@pytest.mark.asyncio
async def test_concurrent_comment_insertions() -> None:
    """
    Simulate high-concurrency insertion of comments into the same draft.
    Uses a shared in-memory DB with multiple concurrent sessions/tasks.
    """
    # 1. Setup Shared DB
    # We use cache=shared so multiple connections see the same data in :memory:
    settings = DatabaseSettings(url="sqlite+aiosqlite:///file:concurrent_test_db?mode=memory&cache=shared&uri=true")
    manager = DatabaseSessionManager(settings)
    manager.init()

    # Capture engine in local variable and assert to satisfy MyPy narrowing
    engine = manager._engine
    assert engine is not None

    # Enable FKs for SQLite on every connect
    @event.listens_for(engine.sync_engine, "connect")
    def _enable_keys(dbapi_connection: Any, connection_record: Any) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    # Create Schema
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # 2. Seed Data (Project & Draft)
    draft_id = uuid4()
    async with manager.session() as session:
        project_repo = SqlAlchemyProjectRepository(session)
        draft_repo = SqlAlchemyDraftRepository(session)

        project = Project(name="Concurrent Project")
        await project_repo.save(project)

        draft = Draft(
            id=draft_id,
            project_id=project.id,
            version_number=1,
            prompt_text="Concurrent Base",
            model_configuration={},
            author_id=uuid4(),
        )
        await draft_repo.save(draft)
        await session.commit()

    # 3. Define Concurrent Worker
    async def save_comment(idx: int) -> None:
        async with manager.session() as session:
            repo = SqlAlchemyCommentRepository(session)
            comment = Comment(
                draft_id=draft_id, target_field="prompt_text", text=f"Concurrent Comment {idx}", author_id=uuid4()
            )
            await repo.save(comment)
            await session.commit()

    # 4. Run Concurrent Tasks
    # SQLite is single-writer, so this tests locking/queueing behavior more than true parallel write,
    # but strictly ensures no data loss or race condition errors in the app logic.
    concurrency_level = 20
    tasks = [save_comment(i) for i in range(concurrency_level)]

    # Run them!
    await asyncio.gather(*tasks)

    # 5. Verify Results
    async with manager.session() as session:
        repo = SqlAlchemyCommentRepository(session)
        comments = await repo.list_by_draft(draft_id)
        assert len(comments) == concurrency_level

        # Verify all texts are present
        texts = {c.text for c in comments}
        expected_texts = {f"Concurrent Comment {i}" for i in range(concurrency_level)}
        assert texts == expected_texts

    # Cleanup
    await manager.close()
