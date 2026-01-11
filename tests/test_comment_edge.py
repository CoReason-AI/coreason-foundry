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
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from coreason_foundry.managers import InMemoryCommentRepository
from coreason_foundry.models import Comment, Draft, Project
from coreason_foundry.repositories import (
    SqlAlchemyCommentRepository,
    SqlAlchemyDraftRepository,
    SqlAlchemyProjectRepository,
)

# --- Model Edge Cases ---


def test_comment_unicode_support() -> None:
    """Test that comments support full Unicode character sets (Emoji, Kanji, etc.)."""
    text = "Reviewing: 🐛 Bug fix needed here. Also, add more ✨ magic. 日本語もOK."
    comment = Comment(draft_id=uuid4(), target_field="prompt_text", text=text, author_id=uuid4())
    assert comment.text == text


def test_comment_large_payload() -> None:
    """Test that comments can handle reasonably large text payloads (e.g., 10KB)."""
    large_text = "A" * 10_000
    comment = Comment(draft_id=uuid4(), target_field="prompt_text", text=large_text, author_id=uuid4())
    assert len(comment.text) == 10_000


# --- Persistence Edge Cases (In-Memory) ---


@pytest.mark.asyncio
async def test_in_memory_ordering_precision() -> None:
    """Verify that list_by_draft strictly respects created_at ordering."""
    repo = InMemoryCommentRepository()
    draft_id = uuid4()

    # Create comments with guaranteed time differences
    # (Since datetime.now() might be fast, we manually ensure gaps if needed,
    # but the repo uses the model's created_at which is set at instantiation)

    c1 = Comment(draft_id=draft_id, target_field="f1", text="First", author_id=uuid4())
    await asyncio.sleep(0.001)  # Ensure tick
    c2 = Comment(draft_id=draft_id, target_field="f1", text="Second", author_id=uuid4())
    await asyncio.sleep(0.001)
    c3 = Comment(draft_id=draft_id, target_field="f1", text="Third", author_id=uuid4())

    # Save out of order
    await repo.save(c2)
    await repo.save(c3)
    await repo.save(c1)

    comments = await repo.list_by_draft(draft_id)
    assert len(comments) == 3
    assert comments[0].text == "First"
    assert comments[1].text == "Second"
    assert comments[2].text == "Third"


# --- Persistence Edge Cases (SQLAlchemy) ---


@pytest.mark.asyncio
async def test_sql_orphan_comment_integrity_error(db_session: AsyncSession) -> None:
    """
    Verify that SQLite enforces Foreign Key constraints.
    Attempting to save a comment for a non-existent Draft ID should raise IntegrityError.
    """
    repo = SqlAlchemyCommentRepository(db_session)

    # Random draft ID that definitely doesn't exist
    orphan_comment = Comment(draft_id=uuid4(), target_field="prompt_text", text="I have no parent", author_id=uuid4())

    with pytest.raises(IntegrityError):
        await repo.save(orphan_comment)


@pytest.mark.asyncio
async def test_sql_unicode_roundtrip(db_session: AsyncSession) -> None:
    """Verify that Emoji/Unicode survives the DB roundtrip."""
    # Setup Parent
    project_repo = SqlAlchemyProjectRepository(db_session)
    draft_repo = SqlAlchemyDraftRepository(db_session)
    comment_repo = SqlAlchemyCommentRepository(db_session)

    project = Project(name="Unicode Project")
    await project_repo.save(project)

    draft = Draft(
        project_id=project.id, version_number=1, prompt_text="base", model_configuration={}, author_id=uuid4()
    )
    await draft_repo.save(draft)

    # Save Unicode Comment
    special_text = "🚀 Launching sequence: 3... 2... 1... 🛑 Abort!"
    comment = Comment(draft_id=draft.id, target_field="prompt_text", text=special_text, author_id=uuid4())
    await comment_repo.save(comment)

    # Fetch
    fetched = await comment_repo.get(comment.id)
    assert fetched is not None
    assert fetched.text == special_text
