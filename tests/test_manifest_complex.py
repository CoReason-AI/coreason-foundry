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

from coreason_foundry.managers import DraftManager
from coreason_foundry.models import Draft, Project


@pytest.mark.asyncio
async def test_manifest_lifecycle_immutability() -> None:
    """
    Complex Test: Simulates a lifecycle where Drafts are created and published.
    Verifies that distinct Draft versions produce distinct Manifest hashes,
    ensuring uniqueness/immutability of the artifacts.
    """
    # Setup Mocks
    uow = MagicMock()
    draft_repo = AsyncMock()
    project_repo = AsyncMock()
    uow.drafts = draft_repo
    uow.projects = project_repo
    uow.__aenter__.return_value = uow
    uow.__aexit__.return_value = None

    manager = DraftManager(uow=uow)

    project_id = uuid4()
    author_id = uuid4()
    project = Project(id=project_id, name="Lifecycle Project")
    project_repo.get.return_value = project

    # 1. Create Draft V1
    draft_v1 = Draft(
        id=uuid4(),
        project_id=project_id,
        version_number=1,
        prompt_text="Prompt V1",
        model_configuration={"temperature": 0.5},
        author_id=author_id,
    )
    draft_repo.get.return_value = draft_v1  # Mock DB return

    # 2. Publish V1
    # Note: manager.publish_draft takes an ID.
    # In this mock, we ensure get(draft_v1.id) returns draft_v1
    def get_side_effect(id: object) -> Draft | None:
        if id == draft_v1.id:
            return draft_v1
        if id == draft_v2.id:
            return draft_v2
        return None

    draft_repo.get.side_effect = get_side_effect

    manifest_v1 = await manager.publish_draft(draft_v1.id)
    hash_v1 = manifest_v1.integrity_hash

    # 3. Create Draft V2 (Identical content, different version)
    draft_v2 = Draft(
        id=uuid4(),
        project_id=project_id,
        version_number=2,
        prompt_text="Prompt V1",  # Same prompt
        model_configuration={"temperature": 0.5},  # Same config
        author_id=author_id,
    )

    # 4. Publish V2
    manifest_v2 = await manager.publish_draft(draft_v2.id)
    hash_v2 = manifest_v2.integrity_hash

    # 5. Verify Distinction
    # Even though content (prompt/config) is effectively same,
    # the Version Number in metadata is different (0.0.1 vs 0.0.2).
    # Thus, hashes MUST differ.
    assert manifest_v1.metadata.version == "0.0.1"
    assert manifest_v2.metadata.version == "0.0.2"
    assert hash_v1 != hash_v2

    # 6. Verify Determinism
    # Re-publishing V1 should yield Hash V1
    manifest_v1_retry = await manager.publish_draft(draft_v1.id)
    assert manifest_v1_retry.integrity_hash == hash_v1


def test_manifest_hashing_determinism_robust() -> None:
    """
    Robust Test: Ensure hashing is deterministic across multiple calls
    and immune to dictionary key ordering variance in input.
    """
    project_id = uuid4()
    author_id = uuid4()

    # Config with keys that might sort differently in python < 3.7 (not issue here, but good practice)
    config = {"z": 1, "a": 2, "m": 3, "temperature": 0.5, "model": "gpt-4"}

    draft = Draft(
        project_id=project_id,
        version_number=1,
        prompt_text="Test",
        model_configuration=config,
        author_id=author_id,
    )

    # Run 100 times to ensure stability
    hashes = set()
    for _ in range(100):
        manifest = draft.to_manifest("Project")
        hashes.add(manifest.integrity_hash)

    assert len(hashes) == 1
