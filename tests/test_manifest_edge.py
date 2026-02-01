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

from coreason_foundry.models import Draft


def test_manifest_unicode_characters() -> None:
    """
    Edge Case: Verify handling of Unicode/Emoji characters in fields.
    Ensures hashing remains stable and serialization works.
    """
    project_id = uuid4()
    author_id = uuid4()

    # 🤖 uses 4 bytes, ☃ uses 3 bytes
    special_prompt = "You are a helpful 🤖 assistant! ☃"
    special_name = "Agent 🚀 Force"

    draft = Draft(
        project_id=project_id,
        version_number=1,
        prompt_text=special_prompt,
        model_configuration={"temperature": 0.7},
        author_id=author_id,
    )

    manifest = draft.to_manifest(project_name=special_name)

    assert manifest.metadata.name == special_name
    # Note: Prompt is dropped in current implementation, but we verify
    # the process didn't crash.
    assert manifest.integrity_hash is not None

    # Verify strict hash stability
    hash1 = manifest.integrity_hash
    hash2 = draft.to_manifest(project_name=special_name).integrity_hash
    assert hash1 == hash2


def test_manifest_config_filtering() -> None:
    """
    Edge Case: Verify that extra fields in Draft.model_configuration
    are ignored (filtered out) by the strict ModelConfig schema.
    """
    project_id = uuid4()
    author_id = uuid4()

    # 'top_p' and 'custom_param' are NOT in ModelConfig
    config = {"model": "gpt-4", "temperature": 0.5, "top_p": 0.9, "custom_param": "should_be_ignored"}

    draft = Draft(
        project_id=project_id,
        version_number=1,
        prompt_text="Prompt",
        model_configuration=config,
        author_id=author_id,
    )

    manifest = draft.to_manifest(project_name="Test")

    # Access raw internal dict if possible or re-dump
    dumped_config = manifest.config.llm_config.model_dump()

    assert "top_p" not in dumped_config
    assert "custom_param" not in dumped_config
    assert dumped_config["temperature"] == 0.5


def test_manifest_temperature_boundaries() -> None:
    """
    Edge Case: Verify temperature clamping/validation logic.
    """
    project_id = uuid4()
    author_id = uuid4()

    # Test Cases: (Input, Expected)
    cases = [
        (0.0, 0.0),  # Lower Bound
        (2.0, 2.0),  # Upper Bound
        (-0.1, 0.7),  # Below Bound -> Fallback
        (2.1, 0.7),  # Above Bound -> Fallback
        ("0.5", 0.7),  # Wrong Type -> Fallback
    ]

    for input_temp, expected_temp in cases:
        draft = Draft(
            project_id=project_id,
            version_number=1,
            prompt_text="Prompt",
            model_configuration={"temperature": input_temp},
            author_id=author_id,
        )

        manifest = draft.to_manifest(project_name="Test")
        assert manifest.config.llm_config.temperature == expected_temp, f"Failed for input: {input_temp}"


def test_manifest_empty_fields() -> None:
    """
    Edge Case: Verify behavior with empty strings.
    """
    project_id = uuid4()
    author_id = uuid4()

    draft = Draft(
        project_id=project_id,
        version_number=1,
        prompt_text="",  # Empty prompt
        model_configuration={},
        author_id=author_id,
    )

    # coreason-manifest might enforce min_length=1 for name
    # We verify if it raises or passes.
    # The schema for AgentMetadata.name is usually strict.

    # 1. Empty Project Name -> Should fail validation
    with pytest.raises(ValueError):
        draft.to_manifest(project_name="")

    # 2. Valid Name, Empty Prompt -> Should pass (since prompt is dropped currently)
    manifest = draft.to_manifest(project_name="Valid")
    assert manifest.metadata.name == "Valid"
