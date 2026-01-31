# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_foundry

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from coreason_manifest.definitions.agent import AgentDefinition

from coreason_foundry.managers import DraftManager
from coreason_foundry.models import Draft, Project


@pytest.mark.asyncio
async def test_publish_draft_success() -> None:
    # Setup
    uow = MagicMock()
    draft_repo = AsyncMock()
    project_repo = AsyncMock()
    uow.drafts = draft_repo
    uow.projects = project_repo

    # Mock context manager
    uow.__aenter__.return_value = uow
    uow.__aexit__.return_value = None

    project_id = uuid4()
    draft_id = uuid4()

    project = Project(id=project_id, name="Test Project")
    draft = Draft(
        id=draft_id,
        project_id=project_id,
        version_number=1,
        prompt_text="System Prompt",
        model_configuration={"temperature": 0.5},
        author_id=uuid4()
    )

    draft_repo.get.return_value = draft
    project_repo.get.return_value = project

    manager = DraftManager(uow=uow)

    # Action
    manifest = await manager.publish_draft(draft_id)

    # Verify
    assert isinstance(manifest, AgentDefinition)
    assert manifest.metadata.name == "Test Project"
    assert manifest.metadata.version == "0.0.1"

    # Verify interactions
    draft_repo.get.assert_called_with(draft_id)
    project_repo.get.assert_called_with(project_id)


@pytest.mark.asyncio
async def test_publish_draft_not_found() -> None:
    uow = MagicMock()
    draft_repo = AsyncMock()
    uow.drafts = draft_repo

    uow.__aenter__.return_value = uow
    uow.__aexit__.return_value = None

    draft_repo.get.return_value = None

    manager = DraftManager(uow=uow)

    with pytest.raises(ValueError, match="Draft .* not found"):
        await manager.publish_draft(uuid4())


@pytest.mark.asyncio
async def test_publish_draft_project_not_found() -> None:
    uow = MagicMock()
    draft_repo = AsyncMock()
    project_repo = AsyncMock()
    uow.drafts = draft_repo
    uow.projects = project_repo

    uow.__aenter__.return_value = uow
    uow.__aexit__.return_value = None

    project_id = uuid4()
    draft = Draft(
        project_id=project_id,
        version_number=1,
        prompt_text="Prompt",
        model_configuration={},
        author_id=uuid4()
    )

    draft_repo.get.return_value = draft
    project_repo.get.return_value = None  # Project missing

    manager = DraftManager(uow=uow)

    with pytest.raises(ValueError, match="Project .* not found"):
        await manager.publish_draft(draft.id)
