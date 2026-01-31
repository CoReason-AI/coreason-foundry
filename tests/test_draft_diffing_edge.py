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

from coreason_foundry.managers import DraftManager
from coreason_foundry.memory import InMemoryUnitOfWork
from coreason_foundry.models import Project


@pytest.fixture
def draft_manager() -> DraftManager:
    uow = InMemoryUnitOfWork()
    return DraftManager(uow)


@pytest.mark.asyncio
async def test_diff_empty_content(draft_manager: DraftManager) -> None:
    """Test diffing against empty strings."""
    author_id = uuid4()
    project = Project(name="Edge Project")
    await draft_manager.project_repo.add(project)

    draft_empty = await draft_manager.create_draft(project.id, "", {}, author_id)
    draft_content = await draft_manager.create_draft(project.id, "Line 1\nLine 2", {}, author_id)

    # Empty -> Content
    diff_add = await draft_manager.compare_versions(draft_empty.id, draft_content.id)
    assert "+Line 1" in diff_add
    assert "+Line 2" in diff_add
    assert "-Line 1" not in diff_add

    # Content -> Empty
    diff_remove = await draft_manager.compare_versions(draft_content.id, draft_empty.id)
    assert "-Line 1" in diff_remove
    assert "-Line 2" in diff_remove
    assert "+Line 1" not in diff_remove


@pytest.mark.asyncio
async def test_diff_unicode_content(draft_manager: DraftManager) -> None:
    """Test diffing with Unicode characters."""
    author_id = uuid4()
    project = Project(name="Unicode Project")
    await draft_manager.project_repo.add(project)

    text_a = "Hello World 🌍\nPython is fun 🐍"
    text_b = "Hello World 🌎\nPython is cool 🐍"

    draft_a = await draft_manager.create_draft(project.id, text_a, {}, author_id)
    draft_b = await draft_manager.create_draft(project.id, text_b, {}, author_id)

    diff = await draft_manager.compare_versions(draft_a.id, draft_b.id)

    assert "-Hello World 🌍" in diff
    assert "+Hello World 🌎" in diff
    assert "-Python is fun 🐍" in diff
    assert "+Python is cool 🐍" in diff


@pytest.mark.asyncio
async def test_diff_whitespace_changes(draft_manager: DraftManager) -> None:
    """Test diffing subtle whitespace changes."""
    author_id = uuid4()
    project = Project(name="Whitespace Project")
    await draft_manager.project_repo.add(project)

    draft_a = await draft_manager.create_draft(project.id, "Line 1", {}, author_id)
    draft_b = await draft_manager.create_draft(project.id, "Line 1 ", {}, author_id)  # Trailing space

    diff = await draft_manager.compare_versions(draft_a.id, draft_b.id)

    assert "-Line 1" in diff
    assert "+Line 1 " in diff


@pytest.mark.asyncio
async def test_diff_multihunk_complex(draft_manager: DraftManager) -> None:
    """Test a diff with multiple separated changes (hunks)."""
    author_id = uuid4()
    project = Project(name="Complex Project")
    await draft_manager.project_repo.add(project)

    # Create a long text with changes at top and bottom
    lines_a = ["Header"] + [f"Line {i}" for i in range(20)] + ["Footer"]
    lines_b = ["Header Modified"] + [f"Line {i}" for i in range(20)] + ["Footer Modified"]

    text_a = "\n".join(lines_a)
    text_b = "\n".join(lines_b)

    draft_a = await draft_manager.create_draft(project.id, text_a, {}, author_id)
    draft_b = await draft_manager.create_draft(project.id, text_b, {}, author_id)

    diff = await draft_manager.compare_versions(draft_a.id, draft_b.id)

    # Check for two distinct change blocks
    assert "-Header" in diff
    assert "+Header Modified" in diff
    assert "-Footer" in diff
    assert "+Footer Modified" in diff

    # The middle should be skipped in the diff output (standard context is 3 lines)
    # So "Line 10" shouldn't be explicit unless it's context.
    # But specifically, we shouldn't see the *entire* middle section duplicated.
    # We check that we have multiple @@ blocks implies checking the structure,
    # but exact string matching of @@ is fragile.
    # Instead, we verify that the middle unchanged lines are NOT marked as + or -
    assert "+Line 10" not in diff
    assert "-Line 10" not in diff


@pytest.mark.asyncio
async def test_diff_large_input_safety(draft_manager: DraftManager) -> None:
    """Test diffing moderately large inputs to ensure no recursion depth or timeout issues."""
    author_id = uuid4()
    project = Project(name="Large Project")
    await draft_manager.project_repo.add(project)

    # 2000 lines
    lines_a = [f"This is line {i}" for i in range(2000)]
    lines_b = list(lines_a)
    lines_b[1000] = "This is line 1000 MODIFIED"

    text_a = "\n".join(lines_a)
    text_b = "\n".join(lines_b)

    draft_a = await draft_manager.create_draft(project.id, text_a, {}, author_id)
    draft_b = await draft_manager.create_draft(project.id, text_b, {}, author_id)

    diff = await draft_manager.compare_versions(draft_a.id, draft_b.id)

    assert "-This is line 1000" in diff
    assert "+This is line 1000 MODIFIED" in diff
