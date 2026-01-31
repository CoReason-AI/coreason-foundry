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
from typing import Any, AsyncGenerator, Dict

import pytest
from coreason_foundry.api.app import app
from coreason_foundry.api.dependencies import get_project_repository
from coreason_foundry.memory import InMemoryProjectRepository
from httpx import ASGITransport, AsyncClient


@pytest.fixture
def override_project_repo() -> AsyncGenerator[InMemoryProjectRepository, None]:
    """
    Fixture to provide a fresh InMemoryProjectRepository for each test.
    """
    repo = InMemoryProjectRepository()
    app.dependency_overrides[get_project_repository] = lambda: repo
    yield repo
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_create_project_validation_error_empty_name(override_project_repo: InMemoryProjectRepository) -> None:
    """
    Test that creating a project with an empty name fails validation.
    """
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/projects/", json={"name": ""})

    # Pydantic min_length=1 should catch this
    assert response.status_code == 422
    data = response.json()
    assert data["detail"][0]["type"] == "string_too_short"


@pytest.mark.asyncio
async def test_create_project_validation_error_missing_field(override_project_repo: InMemoryProjectRepository) -> None:
    """
    Test that creating a project without the 'name' field fails validation.
    """
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/projects/", json={})

    assert response.status_code == 422
    data = response.json()
    assert data["detail"][0]["type"] == "missing"
    assert data["detail"][0]["loc"] == ["body", "name"]


@pytest.mark.asyncio
async def test_get_project_invalid_uuid(override_project_repo: InMemoryProjectRepository) -> None:
    """
    Test that requesting a project with a malformed UUID returns 422.
    """
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/projects/not-a-uuid")

    assert response.status_code == 422
    data = response.json()
    assert data["detail"][0]["type"] == "uuid_parsing"


@pytest.mark.asyncio
async def test_create_project_unicode_emoji(override_project_repo: InMemoryProjectRepository) -> None:
    """
    Test that we can create projects with Unicode characters and Emojis.
    """
    name = "Project 🚀 Mars / 株式会社"
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/projects/", json={"name": name})

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == name

        # Verify retrieval inside the session
        project_id = data["id"]
        response_get = await ac.get(f"/projects/{project_id}")
        assert response_get.status_code == 200
        assert response_get.json()["name"] == name


@pytest.mark.asyncio
async def test_create_projects_concurrently(override_project_repo: InMemoryProjectRepository) -> None:
    """
    Test creating multiple projects concurrently.
    """
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:

        async def create_one(i: int) -> Dict[str, Any]:
            resp = await ac.post("/projects/", json={"name": f"Concurrent Project {i}"})
            assert resp.status_code == 201
            return resp.json()  # type: ignore

        # Run 50 concurrent creations
        tasks = [create_one(i) for i in range(50)]
        results = await asyncio.gather(*tasks)

        assert len(results) == 50
        ids = {r["id"] for r in results}
        assert len(ids) == 50  # All IDs should be unique

        # Verify list count
        list_resp = await ac.get("/projects/")
        assert list_resp.status_code == 200
        assert len(list_resp.json()) == 50


@pytest.mark.asyncio
async def test_list_projects_empty(override_project_repo: InMemoryProjectRepository) -> None:
    """
    Test listing projects when the repository is empty.
    """
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/projects/")

    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_create_project_whitespace_name(override_project_repo: InMemoryProjectRepository) -> None:
    """
    Test creating a project with only whitespace.
    Currently allowed by schema (min_length=1 checks chars), but we should verify behavior.
    """
    name = "   "
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/projects/", json={"name": name})

    # If the schema allows it, it should return 201.
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "   "
