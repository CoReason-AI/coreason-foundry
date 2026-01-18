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
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from coreason_foundry.api.dependencies import (
    get_current_user_id,
    get_draft_manager,
    get_draft_repository,
    get_project_manager,
    get_project_repository,
    get_unit_of_work,
)
from coreason_foundry.interfaces import DraftRepository, ProjectRepository, UnitOfWork
from coreason_foundry.managers import DraftManager, ProjectManager
from coreason_foundry.memory import InMemoryDraftRepository, InMemoryProjectRepository


def test_get_current_user_id_success() -> None:
    user_id = uuid.uuid4()
    result = get_current_user_id(str(user_id))
    assert result == user_id


def test_get_current_user_id_missing() -> None:
    with pytest.raises(HTTPException) as exc:
        get_current_user_id(None)
    assert exc.value.status_code == 401


def test_get_current_user_id_invalid() -> None:
    with pytest.raises(HTTPException) as exc:
        get_current_user_id("invalid-uuid")
    assert exc.value.status_code == 400


def test_get_project_repository() -> None:
    uow = get_unit_of_work()
    repo = get_project_repository(uow)
    assert isinstance(repo, InMemoryProjectRepository)
    # Singleton check within same UoW
    repo2 = get_project_repository(uow)
    assert repo is repo2


def test_get_draft_repository() -> None:
    uow = get_unit_of_work()
    repo = get_draft_repository(uow)
    assert isinstance(repo, InMemoryDraftRepository)
    # Singleton check within same UoW
    repo2 = get_draft_repository(uow)
    assert repo is repo2


def test_get_project_manager() -> None:
    repo = MagicMock(spec=ProjectRepository)
    manager = get_project_manager(repo)
    assert isinstance(manager, ProjectManager)
    assert manager.repository is repo


def test_get_draft_manager() -> None:
    uow = MagicMock(spec=UnitOfWork)
    uow.projects = MagicMock(spec=ProjectRepository)
    uow.drafts = MagicMock(spec=DraftRepository)
    manager = get_draft_manager(uow)
    assert isinstance(manager, DraftManager)
    assert manager.uow is uow
