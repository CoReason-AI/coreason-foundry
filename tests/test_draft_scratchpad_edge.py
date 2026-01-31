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

from coreason_foundry.managers import DraftManager, ProjectManager
from coreason_foundry.memory import InMemoryUnitOfWork


@pytest.mark.asyncio
async def test_scratchpad_empty_string_vs_none() -> None:
    """Verify that an empty string is preserved and distinct from None."""
    # Setup
    uow = InMemoryUnitOfWork()
    manager = DraftManager(uow)
    project_manager = ProjectManager(uow.projects)
    project = await project_manager.create_project("Edge Case Project")
    author_id = uuid4()

    # Draft 1: None (Default)
    draft1 = await manager.create_draft(project.id, "Prompt 1", {}, author_id, scratchpad=None)

    # Draft 2: Empty String
    draft2 = await manager.create_draft(project.id, "Prompt 2", {}, author_id, scratchpad="")

    # Verify
    assert draft1.scratchpad is None
    assert draft2.scratchpad == ""
    assert draft1.scratchpad != draft2.scratchpad

    # Verify Persistence
    saved_d1 = await uow.drafts.get(draft1.id)
    saved_d2 = await uow.drafts.get(draft2.id)
    assert saved_d1 is not None and saved_d1.scratchpad is None
    assert saved_d2 is not None and saved_d2.scratchpad == ""


@pytest.mark.asyncio
async def test_scratchpad_whitespace_preservation() -> None:
    """Verify that whitespace is strictly preserved (critical for Markdown/Code)."""
    uow = InMemoryUnitOfWork()
    manager = DraftManager(uow)
    project = await ProjectManager(uow.projects).create_project("Whitespace Project")

    # Text with mix of tabs, newlines, and trailing spaces
    complex_whitespace = "\n  List Item:\n\t* Indented\n    "

    draft = await manager.create_draft(project.id, "Prompt", {}, uuid4(), scratchpad=complex_whitespace)

    saved = await uow.drafts.get(draft.id)
    assert saved is not None
    assert saved.scratchpad == complex_whitespace
    assert len(saved.scratchpad) == len(complex_whitespace)


@pytest.mark.asyncio
async def test_scratchpad_unicode_and_emojis() -> None:
    """Verify support for Unicode characters and Emojis."""
    uow = InMemoryUnitOfWork()
    manager = DraftManager(uow)
    project = await ProjectManager(uow.projects).create_project("Unicode Project")

    unicode_content = "Engineering Note 📝: \nFixed bug in 'café' module. \n🚀 Ready for deploy! \nひらがな"

    draft = await manager.create_draft(project.id, "Prompt", {}, uuid4(), scratchpad=unicode_content)

    saved = await uow.drafts.get(draft.id)
    assert saved is not None
    assert saved.scratchpad == unicode_content


@pytest.mark.asyncio
async def test_scratchpad_large_payload() -> None:
    """Verify handling of large text content."""
    uow = InMemoryUnitOfWork()
    manager = DraftManager(uow)
    project = await ProjectManager(uow.projects).create_project("Large Payload Project")

    # Create a 100KB string
    large_content = "Line of text.\n" * 5000

    draft = await manager.create_draft(project.id, "Prompt", {}, uuid4(), scratchpad=large_content)

    saved = await uow.drafts.get(draft.id)
    assert saved is not None
    assert saved.scratchpad == large_content
    assert len(saved.scratchpad) >= 5000 * 10


@pytest.mark.asyncio
async def test_scratchpad_no_automatic_inheritance() -> None:
    """
    Verify that a new draft does NOT inherit the scratchpad from the previous version
    unless explicitly passed. This confirms the system expects the client to manage state carry-over.
    """
    uow = InMemoryUnitOfWork()
    manager = DraftManager(uow)
    project = await ProjectManager(uow.projects).create_project("Inheritance Project")
    author_id = uuid4()

    # v1: Has scratchpad
    draft_v1 = await manager.create_draft(project.id, "Prompt v1", {}, author_id, scratchpad="Important Context")

    # v2: Created without specifying scratchpad (simulating client not sending it back)
    draft_v2 = await manager.create_draft(
        project.id,
        "Prompt v2",
        {},
        author_id,
        # scratchpad argument defaults to None
    )

    assert draft_v1.version_number == 1
    assert draft_v1.scratchpad == "Important Context"

    assert draft_v2.version_number == 2
    assert draft_v2.scratchpad is None  # Should NOT be "Important Context"

    # v3: Explicitly "carrying over" logic (simulating client sending it)
    draft_v3 = await manager.create_draft(project.id, "Prompt v3", {}, author_id, scratchpad=draft_v1.scratchpad)

    assert draft_v3.version_number == 3
    assert draft_v3.scratchpad == "Important Context"
