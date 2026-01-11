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
from sqlalchemy.ext.asyncio import AsyncSession

from coreason_foundry.managers import InMemoryCommentRepository
from coreason_foundry.models import Comment
from coreason_foundry.repositories import SqlAlchemyCommentRepository


# Test Data
def make_comment() -> Comment:
    return Comment(
        draft_id=uuid4(),
        target_field="system_prompt",
        text="Needs more gravitas.",
        author_id=uuid4(),
    )


@pytest.mark.asyncio
async def test_in_memory_comment_repository() -> None:
    repo = InMemoryCommentRepository()
    comment = make_comment()

    # Save
    saved = await repo.save(comment)
    assert saved == comment
    assert saved is not comment  # Deep copy check

    # Get
    fetched = await repo.get(comment.id)
    assert fetched == comment

    # List
    comment2 = Comment(draft_id=comment.draft_id, target_field="prompt", text="Another one", author_id=uuid4())
    await repo.save(comment2)

    # Add a comment for a different draft to ensure filtering works
    other_draft_comment = Comment(draft_id=uuid4(), target_field="prompt", text="Other draft", author_id=uuid4())
    await repo.save(other_draft_comment)

    listing = await repo.list_by_draft(comment.draft_id)
    assert len(listing) == 2
    assert comment in listing
    assert comment2 in listing
    assert other_draft_comment not in listing

    # Delete
    deleted = await repo.delete(comment.id)
    assert deleted is True
    assert await repo.get(comment.id) is None

    # Delete non-existent
    assert await repo.delete(uuid4()) is False


@pytest.mark.asyncio
async def test_sqlalchemy_comment_repository(db_session: AsyncSession) -> None:
    repo = SqlAlchemyCommentRepository(db_session)

    from coreason_foundry.models import Draft, Project
    from coreason_foundry.repositories import SqlAlchemyDraftRepository, SqlAlchemyProjectRepository

    # Setup Parents
    project_repo = SqlAlchemyProjectRepository(db_session)
    draft_repo = SqlAlchemyDraftRepository(db_session)

    project = Project(name="Test Project")
    await project_repo.save(project)

    draft = Draft(project_id=project.id, version_number=1, prompt_text="foo", model_configuration={}, author_id=uuid4())
    await draft_repo.save(draft)

    # Test Comment Repo
    comment = Comment(draft_id=draft.id, target_field="prompt_text", text="SQL Test Comment", author_id=uuid4())

    # Save
    saved = await repo.save(comment)
    assert saved.id == comment.id

    # Get
    fetched = await repo.get(comment.id)
    assert fetched is not None
    assert fetched.id == comment.id
    assert fetched.text == comment.text

    # List
    listing = await repo.list_by_draft(draft.id)
    assert len(listing) == 1
    assert listing[0].id == comment.id

    # Delete
    deleted = await repo.delete(comment.id)
    assert deleted is True
    assert await repo.get(comment.id) is None
