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
from coreason_manifest.definitions.agent import AgentDefinition
from pydantic import ValidationError

from coreason_foundry.models import Draft


def test_draft_invalid_tool_uri() -> None:
    """
    Edge Case: Ensure Draft creation fails if tool URI is invalid.
    """
    project_id = uuid4()
    author_id = uuid4()

    with pytest.raises(ValidationError):
        Draft(
            project_id=project_id,
            version_number=1,
            prompt_text="System prompt",
            model_configuration={},
            tools=["not-a-valid-uri"],  # Invalid URI
            author_id=author_id,
        )


def test_to_manifest_defaults() -> None:
    """
    Edge Case: Ensure to_manifest works with empty model_configuration by using defaults.
    """
    project_id = uuid4()
    author_id = uuid4()

    draft = Draft(
        project_id=project_id,
        version_number=1,
        prompt_text="Prompt",
        model_configuration={},  # Empty config
        tools=[],
        author_id=author_id,
    )

    manifest = draft.to_manifest()

    assert isinstance(manifest, AgentDefinition)
    # Check defaults defined in Draft.to_manifest
    topo_dump = manifest.topology.model_dump()
    assert topo_dump["llm_config"]["model"] == "gpt-4"
    assert topo_dump["llm_config"]["temperature"] == 0.7


def test_to_manifest_empty_tools() -> None:
    """
    Edge Case: Ensure to_manifest works with empty tools list.
    """
    project_id = uuid4()
    author_id = uuid4()

    draft = Draft(
        project_id=project_id,
        version_number=1,
        prompt_text="Prompt",
        model_configuration={},
        tools=[],
        author_id=author_id,
    )

    manifest = draft.to_manifest()
    assert len(manifest.dependencies.tools) == 0


def test_to_manifest_extra_config_ignored() -> None:
    """
    Edge Case: Ensure extra keys in model_configuration don't break conversion.
    """
    project_id = uuid4()
    author_id = uuid4()

    config = {
        "model": "gpt-3.5-turbo",
        "temperature": 0.1,
        "max_tokens": 1000,
        "top_p": 0.9,
        "custom_plugin_config": {"enabled": True},
    }

    draft = Draft(
        project_id=project_id,
        version_number=1,
        prompt_text="Prompt",
        model_configuration=config,
        tools=[],
        author_id=author_id,
    )

    manifest = draft.to_manifest()
    topo_dump = manifest.topology.model_dump()

    assert topo_dump["llm_config"]["model"] == "gpt-3.5-turbo"
    assert topo_dump["llm_config"]["temperature"] == 0.1
    # max_tokens and others are not in the standard Kernel ModelConfig, so they are not mapped
    # This confirms we don't crash on extra data
