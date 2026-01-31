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
    get_unit_of_work,
)
from coreason_foundry.memory import (
    InMemoryDraftRepository,
    InMemoryProjectRepository,
    InMemoryUnitOfWork,
)


@pytest_asyncio.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client


@pytest.fixture
def uow() -> InMemoryUnitOfWork:
    return InMemoryUnitOfWork()


@pytest.fixture
def project_repo(uow: InMemoryUnitOfWork) -> InMemoryProjectRepository:
    return uow.projects  # type: ignore


@pytest.fixture
def draft_repo(uow: InMemoryUnitOfWork) -> InMemoryDraftRepository:
    return uow.drafts  # type: ignore


@pytest.fixture(autouse=True)
def override_dependencies(
    uow: InMemoryUnitOfWork,
) -> Generator[None, None, None]:
    app.dependency_overrides[get_unit_of_work] = lambda: uow
    app.dependency_overrides[get_project_repository] = lambda: uow.projects
    app.dependency_overrides[get_draft_repository] = lambda: uow.drafts
    yield
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_compare_drafts_different_projects(
    async_client: AsyncClient, draft_repo: InMemoryDraftRepository
) -> None:
    from coreason_foundry.models import Draft

    author_id = uuid.uuid4()

    # Draft in Project A
    draft1 = Draft(
        project_id=uuid.uuid4(),
        version_number=1,
        prompt_text="Project A",
        model_configuration={},
        author_id=author_id,
    )
    # Draft in Project B
    draft2 = Draft(
        project_id=uuid.uuid4(),
        version_number=1,
        prompt_text="Project B",
        model_configuration={},
        author_id=author_id,
    )

    await draft_repo.add(draft1)
    await draft_repo.add(draft2)

    response = await async_client.get(
        "/drafts/compare", params={"base_id": str(draft1.id), "target_id": str(draft2.id)}
    )

    assert response.status_code == 400
    assert "different projects" in response.json()["detail"]


@pytest.mark.asyncio
async def test_compare_draft_self(async_client: AsyncClient, draft_repo: InMemoryDraftRepository) -> None:
    from coreason_foundry.models import Draft

    draft = Draft(
        project_id=uuid.uuid4(),
        version_number=1,
        prompt_text="Same text",
        model_configuration={},
        author_id=uuid.uuid4(),
    )
    await draft_repo.add(draft)

    response = await async_client.get("/drafts/compare", params={"base_id": str(draft.id), "target_id": str(draft.id)})

    assert response.status_code == 200
    # Diff should be empty (no lines starting with + or - that are content)
    # difflib.unified_diff usually produces headers if "fromfile" and "tofile" are provided
    # even if content is same? No, usually it returns empty list if same.
    # Let's check our implementation: "".join(diff)
    # if empty, it's empty string.
    assert response.json()["diff"] == ""


@pytest.mark.asyncio
async def test_draft_unicode_support(async_client: AsyncClient, project_repo: InMemoryProjectRepository) -> None:
    from coreason_foundry.models import Project

    project = Project(name="Unicode Project")
    await project_repo.add(project)

    user_id = str(uuid.uuid4())
    # Emoji: 🚀, Japanese: こんにちは, Special: \n\t
    prompt_text = "Launch sequence: 🚀\nMessage: こんにちは"
    payload = {
        "prompt_text": prompt_text,
        "model_configuration": {},
        "scratchpad": "📝 Note",
    }
    headers = {"X-User-ID": user_id}

    response = await async_client.post(f"/projects/{project.id}/drafts", json=payload, headers=headers)

    assert response.status_code == 201
    draft_id = response.json()["id"]

    # Retrieve and verify
    get_response = await async_client.get(f"/drafts/{draft_id}")
    assert get_response.status_code == 200
    data = get_response.json()
    assert data["prompt_text"] == prompt_text
    assert data["scratchpad"] == "📝 Note"


@pytest.mark.asyncio
async def test_sequential_versioning(async_client: AsyncClient, project_repo: InMemoryProjectRepository) -> None:
    from coreason_foundry.models import Project

    project = Project(name="Versioning Project")
    await project_repo.add(project)

    user_id = str(uuid.uuid4())
    headers = {"X-User-ID": user_id}

    # Create 3 drafts
    for i in range(1, 4):
        payload = {
            "prompt_text": f"Version {i}",
            "model_configuration": {},
        }
        response = await async_client.post(f"/projects/{project.id}/drafts", json=payload, headers=headers)
        assert response.status_code == 201
        data = response.json()
        assert data["version_number"] == i

        # Verify project pointer immediately
        updated_proj = await project_repo.get(project.id)
        assert updated_proj is not None
        assert str(updated_proj.current_draft_id) == data["id"]


@pytest.mark.asyncio
async def test_create_draft_missing_auth(async_client: AsyncClient) -> None:
    random_id = uuid.uuid4()
    payload = {"prompt_text": "foo", "model_configuration": {}}

    response = await async_client.post(
        f"/projects/{random_id}/drafts",
        json=payload,
        # No headers
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_create_draft_invalid_auth(async_client: AsyncClient) -> None:
    random_id = uuid.uuid4()
    payload = {"prompt_text": "foo", "model_configuration": {}}
    headers = {"X-User-ID": "not-a-uuid"}

    response = await async_client.post(f"/projects/{random_id}/drafts", json=payload, headers=headers)
    assert response.status_code == 400
