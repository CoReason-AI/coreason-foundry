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

from coreason_foundry.managers import InMemoryProjectRepository, ProjectManager


def test_create_project() -> None:
    repo = InMemoryProjectRepository()
    manager = ProjectManager(repo)

    project = manager.create_project("My Agent")

    assert project.name == "My Agent"
    assert project.id is not None
    assert project.created_at is not None
    assert project.current_draft_id is None


def test_get_project() -> None:
    repo = InMemoryProjectRepository()
    manager = ProjectManager(repo)

    project = manager.create_project("Test Agent")
    retrieved = manager.get_project(project.id)

    assert retrieved == project
    assert retrieved.name == "Test Agent"


def test_get_non_existent_project() -> None:
    repo = InMemoryProjectRepository()
    manager = ProjectManager(repo)

    assert manager.get_project(uuid4()) is None


def test_list_projects() -> None:
    repo = InMemoryProjectRepository()
    manager = ProjectManager(repo)

    p1 = manager.create_project("A")
    p2 = manager.create_project("B")

    projects = manager.list_projects()
    assert len(projects) == 2
    assert p1 in projects
    assert p2 in projects
