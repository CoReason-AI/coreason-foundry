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

from coreason_foundry.managers import DraftManager, ProjectManager
from coreason_foundry.memory import InMemoryUnitOfWork
from coreason_foundry.models import Draft, Project


@pytest.mark.asyncio
async def test_create_draft_version_gaps() -> None:
    """
    Verifies that create_draft correctly increments from the highest existing version number,
    even if there are gaps (e.g., v1, v2, v10 -> v11).
    """
    uow = InMemoryUnitOfWork()
    project_repo = uow.projects
    draft_repo = uow.drafts
    project_manager = ProjectManager(project_repo)
    draft_manager = DraftManager(uow)

    project = await project_manager.create_project("Gap Project")
    author_id = uuid4()

    # Manually insert a draft with version 10
    draft_v10 = Draft(
        project_id=project.id,
        version_number=10,
        prompt_text="v10",
        model_configuration={},
        author_id=author_id,
    )
    await draft_repo.add(draft_v10)

    # Create next draft via manager
    draft_next = await draft_manager.create_draft(
        project_id=project.id,
        prompt_text="v11",
        model_configuration={},
        author_id=author_id,
    )

    assert draft_next.version_number == 11
    assert draft_next.project_id == project.id

    # Verify Project points to v11
    updated_project = await project_manager.get_project(project.id)
    assert updated_project is not None
    assert updated_project.current_draft_id == draft_next.id


@pytest.mark.asyncio
async def test_create_draft_concurrent_race_condition() -> None:
    """
    Simulates a race condition where two requests try to create a draft simultaneously.
    Since they both read the same 'latest' version (e.g., 0), they both try to save version 1.
    The database (simulated by InMemoryDraftRepository) should enforce uniqueness and reject one.
    """
    uow = InMemoryUnitOfWork()
    project_repo = uow.projects
    draft_repo = uow.drafts
    project_manager = ProjectManager(project_repo)
    draft_manager = DraftManager(uow)

    project = await project_manager.create_project("Race Project")
    author_id = uuid4()

    # Define a task that creates a draft
    async def create_task() -> Draft:
        return await draft_manager.create_draft(
            project_id=project.id,
            prompt_text="Race",
            model_configuration={},
            author_id=author_id,
        )

    # Run two tasks concurrently.
    results = await asyncio.gather(create_task(), create_task(), return_exceptions=True)

    # Analyze results
    successes = [r for r in results if isinstance(r, Draft)]
    failures = [r for r in results if isinstance(r, Exception)]

    # Case 1: They ran sequentially (no race). One is v1, one is v2.
    if len(successes) == 2:
        versions = sorted([d.version_number for d in successes])
        assert versions == [1, 2]

    # Case 2: They raced. One succeeded (v1), one failed (ValueError: duplicate).
    # This proves the system is robust against producing duplicate v1s.
    elif len(successes) == 1:
        assert successes[0].version_number == 1
        assert len(failures) == 1
        assert isinstance(failures[0], ValueError)
        assert "Unique constraint violation" in str(failures[0])

    else:
        pytest.fail(f"Unexpected results: {results}")


@pytest.mark.asyncio
async def test_duplicate_version_constraint() -> None:
    """
    Explicitly tests the unique constraint enforcement in the repository.
    """
    uow = InMemoryUnitOfWork()
    draft_repo = uow.drafts
    project_id = uuid4()
    author_id = uuid4()

    draft1 = Draft(
        project_id=project_id,
        version_number=1,
        prompt_text="v1",
        model_configuration={},
        author_id=author_id,
    )
    await draft_repo.add(draft1)

    draft_duplicate = Draft(
        project_id=project_id,
        version_number=1,
        prompt_text="v1 dup",
        model_configuration={},
        author_id=author_id,
    )

    with pytest.raises(ValueError, match="Unique constraint violation"):
        await draft_repo.add(draft_duplicate)


@pytest.mark.asyncio
async def test_create_draft_empty_inputs() -> None:
    """
    Tests that empty prompt_text and model_configuration are accepted.
    """
    uow = InMemoryUnitOfWork()
    project_repo = uow.projects
    draft_repo = uow.drafts
    project_manager = ProjectManager(project_repo)
    draft_manager = DraftManager(uow)

    project = await project_manager.create_project("Empty Inputs Project")
    assert project.id is not None

    draft = await draft_manager.create_draft(
        project_id=project.id,
        prompt_text="",
        model_configuration={},
        author_id=uuid4(),
    )

    assert draft.prompt_text == ""
    assert draft.model_configuration == {}
    assert draft.version_number == 1


@pytest.mark.asyncio
async def test_atomic_update_failure_scenario() -> None:
    """
    Simulates a failure during the project update step (after draft persistence).
    This tests the 'atomicity' behavior.
    Since we don't have true transactions in InMemory, we verify the state.

    Now that repositories use deepcopy, we can assert that the repository state
    is unaffected by local mutations if save fails.
    """
    uow = InMemoryUnitOfWork()
    project_repo = uow.projects
    draft_repo = uow.drafts
    project_manager = ProjectManager(project_repo)
    draft_manager = DraftManager(uow)

    project = await project_manager.create_project("Broken Project")
    original_project_state = await project_repo.get(project.id)
    assert original_project_state is not None
    assert original_project_state.current_draft_id is None

    # Mock project_repo.update to fail
    original_update = project_repo.update

    async def failing_update(p: Project) -> Project:
        if p.id == project.id and p.current_draft_id is not None:
            raise RuntimeError("DB Connection Lost")
        return await original_update(p)

    project_repo.update = failing_update  # type: ignore

    with pytest.raises(RuntimeError, match="DB Connection Lost"):
        await draft_manager.create_draft(
            project_id=project.id,
            prompt_text="Will Fail",
            model_configuration={},
            author_id=uuid4(),
        )

    # Verify Draft was persisted (Step 3 succeeded)
    drafts = await draft_repo.list_by_project(project.id)
    assert len(drafts) == 1
    assert drafts[0].version_number == 1

    # Verify Project in Repository still points to None (Step 4 failed to persist)
    # Because InMemoryProjectRepository saves a copy, failing to call save means
    # the internal state remains untouched, even if the 'project' object in create_draft was mutated.
    current_project_state = await project_repo.get(project.id)
    assert current_project_state is not None
    assert current_project_state.current_draft_id is None
