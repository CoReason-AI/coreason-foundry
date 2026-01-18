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

from coreason_foundry.models import Draft, Project
from coreason_foundry.repositories import SqlAlchemyDraftRepository, SqlAlchemyProjectRepository


@pytest.mark.asyncio
async def test_draft_unique_version_constraint(db_session: AsyncSession) -> None:
    """
    Complex Scenario: Concurrent/Duplicate Versioning
    Ensure that the database enforces the unique constraint (project_id, version_number).
    """
    project_repo = SqlAlchemyProjectRepository(db_session)
    draft_repo = SqlAlchemyDraftRepository(db_session)

    # Setup Project
    project = Project(name="Constraint Test Project")
    await project_repo.add(project)

    # Save Draft V1
    draft1 = Draft(
        project_id=project.id,
        version_number=1,
        prompt_text="Original",
        model_configuration={},
        author_id=uuid.uuid4(),
    )
    await draft_repo.add(draft1)

    # Attempt to Save Draft V1 again (different ID, same version)
    draft_duplicate = Draft(
        project_id=project.id,
        version_number=1,  # COLLISION
        prompt_text="Collision",
        model_configuration={},
        author_id=uuid.uuid4(),
    )

    with pytest.raises(IntegrityError):
        await draft_repo.add(draft_duplicate)


@pytest.mark.asyncio
async def test_draft_foreign_key_violation(db_session: AsyncSession) -> None:
    """
    Complex Scenario: Referential Integrity
    Ensure that we cannot create a Draft for a non-existent Project.
    """
    draft_repo = SqlAlchemyDraftRepository(db_session)
    non_existent_project_id = uuid.uuid4()

    draft = Draft(
        project_id=non_existent_project_id,
        version_number=1,
        prompt_text="Orphan",
        model_configuration={},
        author_id=uuid.uuid4(),
    )

    with pytest.raises(IntegrityError):
        await draft_repo.add(draft)


@pytest.mark.asyncio
async def test_data_fidelity_unicode_and_json(db_session: AsyncSession) -> None:
    """
    Complex Scenario: Data Fidelity
    Verify storage of Unicode (Emoji, diverse scripts) and complex/nested JSON structures.
    """
    project_repo = SqlAlchemyProjectRepository(db_session)
    draft_repo = SqlAlchemyDraftRepository(db_session)

    # 1. Project with Unicode Name
    project_name = "Project 🚀 (プロジェクタ)"
    project = Project(name=project_name)
    await project_repo.add(project)

    fetched_project = await project_repo.get(project.id)
    assert fetched_project is not None
    assert fetched_project.name == project_name

    # 2. Draft with Complex JSON and Unicode Text
    complex_config = {
        "parameters": {
            "temperature": 0.7,
            "stop_sequences": ["\n", "User:"],
            "nested": {"a": [1, 2, 3], "b": None},
        },
        "tags": ["🤖", "AI"],
    }

    prompt_text = "System: 你好! \nUser: Hello 🌍"

    draft = Draft(
        project_id=project.id,
        version_number=1,
        prompt_text=prompt_text,
        model_configuration=complex_config,
        author_id=uuid.uuid4(),
    )
    await draft_repo.add(draft)

    fetched_draft = await draft_repo.get(draft.id)
    assert fetched_draft is not None
    assert fetched_draft.prompt_text == prompt_text
    assert fetched_draft.model_configuration == complex_config
    # Deep check on JSON equality
    assert fetched_draft.model_configuration["parameters"]["nested"]["a"] == [1, 2, 3]
    assert fetched_draft.model_configuration["tags"][0] == "🤖"
