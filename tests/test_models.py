# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_foundry

from datetime import datetime
from uuid import uuid4

import pytest
from coreason_foundry.models import Draft
from pydantic import ValidationError


def test_draft_creation() -> None:
    project_id = uuid4()
    author_id = uuid4()
    config = {"temperature": 0.7, "max_tokens": 100}

    draft = Draft(
        project_id=project_id,
        version_number=1,
        prompt_text="System prompt...",
        model_configuration=config,
        tools=["https://example.com/tool"],
        author_id=author_id,
    )

    assert draft.id is not None
    assert draft.created_at is not None
    assert isinstance(draft.created_at, datetime)
    assert draft.project_id == project_id
    assert draft.version_number == 1
    assert draft.prompt_text == "System prompt..."
    assert draft.model_configuration == config
    assert [str(t) for t in draft.tools] == ["https://example.com/tool"]
    assert draft.author_id == author_id


def test_draft_validation_missing_fields() -> None:
    with pytest.raises(ValidationError):
        # Missing required fields like project_id, author_id, etc.
        Draft(version_number=1, prompt_text="Test")


def test_draft_config_flexibility() -> None:
    """Ensure model_configuration accepts arbitrary dictionary structures."""
    draft = Draft(
        project_id=uuid4(),
        version_number=1,
        prompt_text="Test",
        model_configuration={"nested": {"key": "value"}, "list": [1, 2, 3]},
        author_id=uuid4(),
    )
    assert draft.model_configuration["nested"]["key"] == "value"
