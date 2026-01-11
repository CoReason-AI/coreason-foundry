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
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from coreason_foundry.db.models import ProjectORM
from coreason_foundry.models import Draft
from coreason_foundry.repositories import SqlAlchemyDraftRepository


@pytest.mark.asyncio
async def test_unique_version_constraint(db_session: AsyncSession) -> None:
    # Setup Project
    project_id = uuid.uuid4()
    project_orm = ProjectORM(id=project_id, name="Test Project Unique")
    db_session.add(project_orm)
    await db_session.flush()

    repo = SqlAlchemyDraftRepository(db_session)

    # Save V1
    draft1 = Draft(
        id=uuid.uuid4(),
        project_id=project_id,
        version_number=1,
        prompt_text="V1",
        model_configuration={},
        author_id=uuid.uuid4(),
    )
    await repo.save(draft1)

    # Try Save Duplicate V1 (Different ID)
    draft1_duplicate = Draft(
        id=uuid.uuid4(),
        project_id=project_id,
        version_number=1,
        prompt_text="V1 Duplicate",
        model_configuration={},
        author_id=uuid.uuid4(),
    )

    with pytest.raises(IntegrityError):
        await repo.save(draft1_duplicate)


@pytest.mark.asyncio
async def test_foreign_key_violation(db_session: AsyncSession) -> None:
    repo = SqlAlchemyDraftRepository(db_session)

    # Draft for non-existent project
    draft_orphan = Draft(
        id=uuid.uuid4(),
        project_id=uuid.uuid4(),  # Random UUID
        version_number=1,
        prompt_text="Orphan",
        model_configuration={},
        author_id=uuid.uuid4(),
    )

    with pytest.raises(IntegrityError):
        await repo.save(draft_orphan)


@pytest.mark.asyncio
async def test_complex_json_serialization(db_session: AsyncSession) -> None:
    # Setup Project
    project_id = uuid.uuid4()
    project_orm = ProjectORM(id=project_id, name="Test Project JSON")
    db_session.add(project_orm)
    await db_session.flush()

    repo = SqlAlchemyDraftRepository(db_session)

    complex_config = {
        "parameters": {"temperature": 0.7, "stop_sequences": ["\n", "User:"], "logit_bias": {"50256": -100}},
        "metadata": {"tags": ["prod", "v1"], "nested_list": [{"a": 1}, {"b": None}]},
        "enabled": True,
        "null_value": None,
    }

    draft = Draft(
        id=uuid.uuid4(),
        project_id=project_id,
        version_number=1,
        prompt_text="Complex JSON",
        model_configuration=complex_config,
        author_id=uuid.uuid4(),
    )

    saved = await repo.save(draft)

    # Fetch back
    # We create a new session or clear identity map to ensure we fetch from DB?
    # But repo.get executes a SELECT, so it should be fine.

    fetched = await repo.get(saved.id)
    assert fetched is not None
    assert fetched.model_configuration == complex_config
    assert fetched.model_configuration["parameters"]["temperature"] == 0.7
    assert fetched.model_configuration["metadata"]["nested_list"][1]["b"] is None


@pytest.mark.asyncio
async def test_large_prompt_text(db_session: AsyncSession) -> None:
    # Setup Project
    project_id = uuid.uuid4()
    project_orm = ProjectORM(id=project_id, name="Test Project Large")
    db_session.add(project_orm)
    await db_session.flush()

    repo = SqlAlchemyDraftRepository(db_session)

    large_text = "A" * 100000  # 100KB string

    draft = Draft(
        id=uuid.uuid4(),
        project_id=project_id,
        version_number=1,
        prompt_text=large_text,
        model_configuration={},
        author_id=uuid.uuid4(),
    )

    await repo.save(draft)

    fetched = await repo.get(draft.id)
    assert fetched is not None
    assert len(fetched.prompt_text) == 100000
    assert fetched.prompt_text == large_text
