# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_foundry

import pytest
from httpx import ASGITransport, AsyncClient
from uuid import uuid4
from typing import AsyncGenerator

from coreason_foundry.api.app import app
from coreason_foundry.api.dependencies import get_project_repository
from coreason_foundry.managers import InMemoryProjectRepository


@pytest.fixture
def override_project_repo() -> AsyncGenerator[InMemoryProjectRepository, None]:
    """
    Fixture to provide a fresh InMemoryProjectRepository for each test.
    This ensures test isolation.
    """
    repo = InMemoryProjectRepository()
    app.dependency_overrides[get_project_repository] = lambda: repo
    yield repo
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_create_project(override_project_repo: InMemoryProjectRepository) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/projects/", json={"name": "Test Project"})

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Project"
    assert "id" in data
    assert "created_at" in data
    assert data["current_draft_id"] is None


@pytest.mark.asyncio
async def test_list_projects(override_project_repo: InMemoryProjectRepository) -> None:
    # Create two projects
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        await ac.post("/projects/", json={"name": "Project 1"})
        await ac.post("/projects/", json={"name": "Project 2"})

        response = await ac.get("/projects/")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    names = [p["name"] for p in data]
    assert "Project 1" in names
    assert "Project 2" in names


@pytest.mark.asyncio
async def test_get_project(override_project_repo: InMemoryProjectRepository) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Create a project
        create_resp = await ac.post("/projects/", json={"name": "Target Project"})
        project_id = create_resp.json()["id"]

        # Get the project
        response = await ac.get(f"/projects/{project_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == project_id
    assert data["name"] == "Target Project"


@pytest.mark.asyncio
async def test_get_project_not_found(override_project_repo: InMemoryProjectRepository) -> None:
    random_id = uuid4()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get(f"/projects/{random_id}")

    assert response.status_code == 404
    assert response.json()["detail"] == "Project not found"

@pytest.mark.asyncio
async def test_default_dependency_injection() -> None:
    """
    Test that the default dependency injection works without override.
    This covers the `get_project_repository` function.
    """
    # Clear overrides just in case
    app.dependency_overrides = {}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # We can't guarantee state is empty because it's a singleton in-memory repo
        # that might persist across tests if not handled carefully,
        # BUT pytest-asyncio runs each test in a loop.
        # However, `lru_cache` is global.
        # So we should just verify we can make a call.

        response = await ac.post("/projects/", json={"name": "Default Dependency Project"})
        assert response.status_code == 201

        response_list = await ac.get("/projects/")
        assert response_list.status_code == 200
        data = response_list.json()
        assert any(p["name"] == "Default Dependency Project" for p in data)
