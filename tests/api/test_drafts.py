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
from typing import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from coreason_foundry.api.app import app
from coreason_foundry.api.dependencies import (
    get_draft_repository,
    get_project_repository,
)
from coreason_foundry.managers import InMemoryDraftRepository, InMemoryProjectRepository


@pytest_asyncio.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client


@pytest.fixture
def project_repo() -> InMemoryProjectRepository:
    return InMemoryProjectRepository()


@pytest.fixture
def draft_repo() -> InMemoryDraftRepository:
    return InMemoryDraftRepository()


@pytest.fixture(autouse=True)
def override_dependencies(
    project_repo: InMemoryProjectRepository, draft_repo: InMemoryDraftRepository
) -> Generator[None, None, None]:
    app.dependency_overrides[get_project_repository] = lambda: project_repo
    app.dependency_overrides[get_draft_repository] = lambda: draft_repo
    yield
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_create_draft(async_client: AsyncClient, project_repo: InMemoryProjectRepository) -> None:
    # Create a project first
    from coreason_foundry.models import Project

    project = Project(name="Test Project")
    await project_repo.save(project)

    user_id = str(uuid.uuid4())
    payload = {
        "prompt_text": "System prompt...",
        "model_configuration": {"temperature": 0.7},
        "scratchpad": "Notes",
    }
    headers = {"X-User-ID": user_id}

    response = await async_client.post(f"/projects/{project.id}/drafts", json=payload, headers=headers)

    assert response.status_code == 201
    data = response.json()
    assert data["project_id"] == str(project.id)
    assert data["version_number"] == 1
    assert data["author_id"] == user_id
    assert data["prompt_text"] == payload["prompt_text"]

    # Verify project pointer updated
    updated_project = await project_repo.get(project.id)
    assert updated_project is not None
    assert updated_project.current_draft_id == uuid.UUID(data["id"])


@pytest.mark.asyncio
async def test_create_draft_project_not_found(async_client: AsyncClient) -> None:
    user_id = str(uuid.uuid4())
    payload = {
        "prompt_text": "System prompt...",
        "model_configuration": {"temperature": 0.7},
    }
    headers = {"X-User-ID": user_id}
    random_id = uuid.uuid4()

    response = await async_client.post(f"/projects/{random_id}/drafts", json=payload, headers=headers)

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_list_drafts(
    async_client: AsyncClient, project_repo: InMemoryProjectRepository, draft_repo: InMemoryDraftRepository
) -> None:
    # Setup
    from coreason_foundry.models import Draft, Project

    project = Project(name="Test Project")
    await project_repo.save(project)

    author_id = uuid.uuid4()
    draft1 = Draft(
        project_id=project.id,
        version_number=1,
        prompt_text="v1",
        model_configuration={},
        author_id=author_id,
    )
    draft2 = Draft(
        project_id=project.id,
        version_number=2,
        prompt_text="v2",
        model_configuration={},
        author_id=author_id,
    )
    await draft_repo.save(draft1)
    await draft_repo.save(draft2)

    response = await async_client.get(f"/projects/{project.id}/drafts")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["version_number"] == 1
    assert data[1]["version_number"] == 2


@pytest.mark.asyncio
async def test_get_draft(async_client: AsyncClient, draft_repo: InMemoryDraftRepository) -> None:
    from coreason_foundry.models import Draft

    draft = Draft(
        project_id=uuid.uuid4(),
        version_number=1,
        prompt_text="v1",
        model_configuration={},
        author_id=uuid.uuid4(),
    )
    await draft_repo.save(draft)

    response = await async_client.get(f"/drafts/{draft.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(draft.id)


@pytest.mark.asyncio
async def test_compare_drafts(async_client: AsyncClient, draft_repo: InMemoryDraftRepository) -> None:
    from coreason_foundry.models import Draft

    project_id = uuid.uuid4()
    author_id = uuid.uuid4()

    draft1 = Draft(
        project_id=project_id,
        version_number=1,
        prompt_text="Hello\nWorld",
        model_configuration={},
        author_id=author_id,
    )
    draft2 = Draft(
        project_id=project_id,
        version_number=2,
        prompt_text="Hello\nCoReason",
        model_configuration={},
        author_id=author_id,
    )
    await draft_repo.save(draft1)
    await draft_repo.save(draft2)

    response = await async_client.get(
        "/drafts/compare", params={"base_id": str(draft1.id), "target_id": str(draft2.id)}
    )

    assert response.status_code == 200
    data = response.json()
    # Expected diff:
    # --- Draft v1
    # +++ Draft v2
    # @@ -1,2 +1,2 @@
    #  Hello
    # -World
    # +CoReason

    assert "--- Draft v1" in data["diff"]
    assert "+++ Draft v2" in data["diff"]
    assert "-World" in data["diff"]
    assert "+CoReason" in data["diff"]


@pytest.mark.asyncio
async def test_compare_drafts_invalid(async_client: AsyncClient) -> None:
    random_id = uuid.uuid4()
    response = await async_client.get(
        "/drafts/compare", params={"base_id": str(random_id), "target_id": str(random_id)}
    )
    assert response.status_code == 400
