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
from coreason_foundry.db.models import ProjectORM
from coreason_foundry.models import Draft
from coreason_foundry.repositories import SqlAlchemyDraftRepository
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_draft_repository_save_and_get(db_session: AsyncSession) -> None:
    # Setup Project
    project_id = uuid.uuid4()
    project_orm = ProjectORM(id=project_id, name="Test Project")
    db_session.add(project_orm)
    await db_session.flush()

    repo = SqlAlchemyDraftRepository(db_session)
    draft_id = uuid.uuid4()
    author_id = uuid.uuid4()

    draft = Draft(
        id=draft_id,
        project_id=project_id,
        version_number=1,
        prompt_text="System Prompt",
        model_configuration={"temperature": 0.7},
        author_id=author_id,
        created_at=datetime.now(timezone.utc),
    )

    # Save
    saved_draft = await repo.add(draft)
    assert saved_draft.id == draft_id
    assert saved_draft.version_number == 1
    assert saved_draft.model_configuration == {"temperature": 0.7}

    # Get
    fetched_draft = await repo.get(draft_id)
    assert fetched_draft is not None
    assert fetched_draft.id == draft_id
    assert fetched_draft.prompt_text == "System Prompt"
    assert fetched_draft.project_id == project_id

    # Get Non Existent
    missing_draft = await repo.get(uuid.uuid4())
    assert missing_draft is None


@pytest.mark.asyncio
async def test_draft_repository_list_by_project(db_session: AsyncSession) -> None:
    # Setup Project
    project_id = uuid.uuid4()
    project_orm = ProjectORM(id=project_id, name="Test Project List")
    db_session.add(project_orm)
    await db_session.flush()

    repo = SqlAlchemyDraftRepository(db_session)

    # Create Drafts
    draft1 = Draft(
        id=uuid.uuid4(),
        project_id=project_id,
        version_number=1,
        prompt_text="V1",
        model_configuration={},
        author_id=uuid.uuid4(),
    )
    draft2 = Draft(
        id=uuid.uuid4(),
        project_id=project_id,
        version_number=2,
        prompt_text="V2",
        model_configuration={},
        author_id=uuid.uuid4(),
    )

    await repo.add(draft1)
    await repo.add(draft2)

    # List
    drafts = await repo.list_by_project(project_id)
    assert len(drafts) == 2
    assert drafts[0].version_number == 1
    assert drafts[1].version_number == 2


@pytest.mark.asyncio
async def test_draft_repository_get_latest_version(db_session: AsyncSession) -> None:
    # Setup Project
    project_id = uuid.uuid4()
    project_orm = ProjectORM(id=project_id, name="Test Project Version")
    db_session.add(project_orm)
    await db_session.flush()

    repo = SqlAlchemyDraftRepository(db_session)

    # Empty
    latest = await repo.get_latest_version(project_id)
    assert latest is None

    # Add V1
    draft1 = Draft(
        id=uuid.uuid4(),
        project_id=project_id,
        version_number=1,
        prompt_text="V1",
        model_configuration={},
        author_id=uuid.uuid4(),
    )
    await repo.add(draft1)

    latest = await repo.get_latest_version(project_id)
    assert latest == 1

    # Add V2
    draft2 = Draft(
        id=uuid.uuid4(),
        project_id=project_id,
        version_number=2,
        prompt_text="V2",
        model_configuration={},
        author_id=uuid.uuid4(),
    )
    await repo.add(draft2)

    latest = await repo.get_latest_version(project_id)
    assert latest == 2
