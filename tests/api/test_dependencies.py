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
)
from coreason_foundry.managers import (
    DraftManager,
    DraftRepository,
    InMemoryDraftRepository,
    InMemoryProjectRepository,
    ProjectManager,
    ProjectRepository,
)


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
    repo = get_project_repository()
    assert isinstance(repo, InMemoryProjectRepository)
    # Singleton check
    repo2 = get_project_repository()
    assert repo is repo2


def test_get_draft_repository() -> None:
    repo = get_draft_repository()
    assert isinstance(repo, InMemoryDraftRepository)
    # Singleton check
    repo2 = get_draft_repository()
    assert repo is repo2


def test_get_project_manager() -> None:
    repo = MagicMock(spec=ProjectRepository)
    manager = get_project_manager(repo)
    assert isinstance(manager, ProjectManager)
    assert manager.repository is repo


def test_get_draft_manager() -> None:
    p_repo = MagicMock(spec=ProjectRepository)
    d_repo = MagicMock(spec=DraftRepository)
    manager = get_draft_manager(p_repo, d_repo)
    assert isinstance(manager, DraftManager)
    assert manager.project_repo is p_repo
    assert manager.draft_repo is d_repo
