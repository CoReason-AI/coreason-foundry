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
from pydantic import ValidationError

from coreason_foundry.models import Comment


def test_comment_creation_success() -> None:
    """Test valid comment creation."""
    comment = Comment(draft_id=uuid4(), target_field="prompt_text", text="This is a test comment", author_id=uuid4())
    assert isinstance(comment.id, type(uuid4()))
    assert isinstance(comment.created_at, datetime)
    assert comment.text == "This is a test comment"


def test_comment_validation_empty_text() -> None:
    """Test that empty comment text raises ValidationError."""
    with pytest.raises(ValidationError) as exc:
        Comment(draft_id=uuid4(), target_field="prompt_text", text="   ", author_id=uuid4())
    assert "Comment text cannot be empty" in str(exc.value)


def test_comment_immutability() -> None:
    """Test that comment fields cannot be modified after creation."""
    comment = Comment(draft_id=uuid4(), target_field="prompt_text", text="Original text", author_id=uuid4())
    with pytest.raises(ValidationError):
        object.__setattr__(comment, "text", "New text")
