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
async def test_draft_repository_save_and_get_tools(db_session: AsyncSession) -> None:
    # Setup Project
    project_id = uuid.uuid4()
    project_orm = ProjectORM(id=project_id, name="Test Project Tools")
    db_session.add(project_orm)
    await db_session.flush()

    repo = SqlAlchemyDraftRepository(db_session)
    draft_id = uuid.uuid4()
    author_id = uuid.uuid4()

    tools = ["https://example.com/tool/1", "https://example.com/tool/2"]

    draft = Draft(
        id=draft_id,
        project_id=project_id,
        version_number=1,
        prompt_text="System Prompt",
        model_configuration={"temperature": 0.7},
        tools=tools,
        author_id=author_id,
        created_at=datetime.now(timezone.utc),
    )

    # Save
    await repo.add(draft)

    # Get
    fetched_draft = await repo.get(draft_id)
    assert fetched_draft is not None
    assert fetched_draft.id == draft_id
    assert len(fetched_draft.tools) == 2
    assert str(fetched_draft.tools[0]) == tools[0]
    assert str(fetched_draft.tools[1]) == tools[1]
