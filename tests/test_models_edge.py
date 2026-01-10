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

import pytest
from pydantic import ValidationError

from coreason_foundry.models import Draft


def test_draft_immutability() -> None:
    """Verify that Draft instances are immutable."""
    draft = Draft(
        project_id=uuid4(), version_number=1, prompt_text="Original", model_configuration={}, author_id=uuid4()
    )

    with pytest.raises(ValidationError):
        draft.prompt_text = "Modified"


def test_draft_version_positive() -> None:
    """Verify that version number must be positive."""
    with pytest.raises(ValidationError):
        Draft(project_id=uuid4(), version_number=0, prompt_text="Test", model_configuration={}, author_id=uuid4())

    with pytest.raises(ValidationError):
        Draft(project_id=uuid4(), version_number=-1, prompt_text="Test", model_configuration={}, author_id=uuid4())


def test_draft_complex_configuration() -> None:
    """Verify handling of complex, deeply nested configuration objects."""
    complex_config = {
        "layers": [
            {"type": "attention", "params": {"heads": 8, "dropout": 0.1}},
            {"type": "feedforward", "params": {"hidden_dim": 2048}},
        ],
        "meta": {"version": "1.0", "flags": [True, False, None], "extra": {"a": {"b": {"c": "deep"}}}},
    }

    draft = Draft(
        project_id=uuid4(),
        version_number=1,
        prompt_text="Complex Config Agent",
        model_configuration=complex_config,
        author_id=uuid4(),
    )

    assert draft.model_configuration == complex_config
    assert draft.model_configuration["meta"]["extra"]["a"]["b"]["c"] == "deep"


def test_draft_large_payload() -> None:
    """Verify that the model can handle reasonably large text payloads."""
    large_text = "x" * 1_000_000  # 1MB string

    draft = Draft(
        project_id=uuid4(), version_number=1, prompt_text=large_text, model_configuration={}, author_id=uuid4()
    )

    assert len(draft.prompt_text) == 1_000_000
