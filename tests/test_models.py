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
from coreason_manifest.definitions.agent import AgentDefinition
from pydantic import ValidationError

from coreason_foundry.models import Draft


def test_draft_creation() -> None:
    project_id = uuid4()
    author_id = uuid4()
    config = {"temperature": 0.7, "max_tokens": 100}

    draft = Draft(
        project_id=project_id,
        version_number=1,
        prompt_text="System prompt...",
        model_configuration=config,
        author_id=author_id,
    )

    assert draft.id is not None
    assert draft.created_at is not None
    assert isinstance(draft.created_at, datetime)
    assert draft.project_id == project_id
    assert draft.version_number == 1
    assert draft.prompt_text == "System prompt..."
    assert draft.model_configuration == config
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


def test_draft_to_manifest_conversion() -> None:
    project_id = uuid4()
    author_id = uuid4()
    config = {
        "temperature": 0.7,
        "tools": [
            {
                "name": "search",
                "description": "Search the web",
                "parameters": {"type": "object"},
            }
        ],
    }

    draft = Draft(
        project_id=project_id,
        version_number=1,
        prompt_text="You are a helpful assistant.",
        model_configuration=config,
        author_id=author_id,
    )

    manifest = draft.to_manifest(project_name="Test Project")

    assert isinstance(manifest, AgentDefinition)
    assert manifest.metadata.name == "Test Project"
    assert manifest.metadata.version == "0.0.1"

    # Verify LLM Config mapping
    assert manifest.config.llm_config.temperature == 0.7
    assert manifest.config.llm_config.model == "gpt-4" # default

    # Verify Skeleton Topology
    assert len(manifest.config.nodes) == 1
    assert manifest.config.nodes[0].id == "main"
    assert manifest.config.nodes[0].type == "logic"

    # Verify dependencies are empty (tools dropped due to schema limitation)
    assert len(manifest.dependencies.tools) == 0

    assert manifest.integrity_hash is not None


def test_draft_to_manifest_no_tools() -> None:
    project_id = uuid4()
    author_id = uuid4()
    config = {"temperature": 0.5, "model": "gpt-3.5-turbo"}

    draft = Draft(
        project_id=project_id,
        version_number=2,
        prompt_text="Prompt",
        model_configuration=config,
        author_id=author_id,
    )

    manifest = draft.to_manifest(project_name="Test Project")
    assert manifest.metadata.version == "0.0.2"
    assert manifest.config.llm_config.model == "gpt-3.5-turbo"
    assert manifest.config.llm_config.temperature == 0.5


def test_draft_to_manifest_invalid_temperature() -> None:
    project_id = uuid4()
    author_id = uuid4()
    # Temperature out of range (must be 0.0 to 2.0)
    config = {"temperature": 3.0}

    draft = Draft(
        project_id=project_id,
        version_number=1,
        prompt_text="Prompt",
        model_configuration=config,
        author_id=author_id,
    )

    manifest = draft.to_manifest(project_name="Test Project")
    # Should fallback to 0.7
    assert manifest.config.llm_config.temperature == 0.7
